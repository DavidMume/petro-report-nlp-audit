"""Exploratory NLP: corpus statistics, term frequencies, TF-IDF, n-grams,
lexicon-based framing / certainty / attribution / causal-language tagging,
and exploratory sentiment.

All outputs here are DESCRIPTIVE. None of these functions is used to assert
that the document is biased, deceptive or truthful — see
documents/methodology.md §"NLP methodology" and §"Causality".
"""

from __future__ import annotations

import re
from collections import Counter

import numpy as np
import pandas as pd

from src import lexicons as lx

# Kept for backwards compatibility with the scaffold / tests.
CAUSAL_MARKERS_ES = lx.CAUSAL_MARKERS_CORE

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:-[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*")


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def _phrase_regex(phrases: list[str]) -> re.Pattern:
    alts = sorted({re.escape(p.lower()) for p in phrases}, key=len, reverse=True)
    return re.compile(r"(?<![\wáéíóúñü])(" + "|".join(alts) + r")(?![\wáéíóúñü])")


def count_phrases(text: str, phrases: list[str]) -> list[str]:
    return _phrase_regex(phrases).findall(text.lower())


# --- Basic statistics ---------------------------------------------------------

def mattr(tokens: list[str], window: int = 500) -> float:
    """Moving-average type-token ratio (Covington & McFall 2010)."""
    if len(tokens) < window:
        return len(set(tokens)) / max(len(tokens), 1)
    counts = Counter(tokens[:window])
    ratios = [len(counts) / window]
    for i in range(window, len(tokens)):
        counts[tokens[i]] += 1
        old = tokens[i - window]
        counts[old] -= 1
        if counts[old] == 0:
            del counts[old]
        ratios.append(len(counts) / window)
    return float(np.mean(ratios))


def compute_basic_stats(corpus_df: pd.DataFrame, paragraphs_df: pd.DataFrame, n_pages: int) -> dict:
    tokens = [w.lower() for t in corpus_df.clean_text for w in words(t)]
    sent_len = corpus_df.clean_text.map(lambda t: len(words(t)))
    lemmas = [w for t in corpus_df.lemma_text for w in t.split()]
    c = Counter(tokens)
    body_paras = paragraphs_df[paragraphs_df.block_type.isin(["body", "list_item"])]
    return {
        "pages_total": n_pages,
        "pages_with_analytic_text": int(corpus_df.page.nunique()),
        "paragraphs": int(len(body_paras)),
        "sentences": int(len(corpus_df)),
        "words": int(len(tokens)),
        "mean_sentence_length_words": round(float(sent_len.mean()), 2),
        "median_sentence_length_words": float(sent_len.median()),
        "sd_sentence_length_words": round(float(sent_len.std()), 2),
        "mean_paragraph_length_words": round(float(body_paras.n_words.mean()), 2),
        "vocabulary_word_types": len(c),
        "type_token_ratio": round(len(c) / max(len(tokens), 1), 4),
        "mattr_500": round(mattr(tokens, 500), 4),
        "hapax_legomena": sum(1 for v in c.values() if v == 1),
        "lemma_types_content": len(set(lemmas)),
        "lemma_tokens_content": len(lemmas),
        "lexical_density": round(len(lemmas) / max(len(tokens), 1), 4),
        "sentences_with_numbers": int((corpus_df.numbers != "[]").sum()),
    }


def compute_term_frequencies(corpus_df: pd.DataFrame, column: str = "lemma_text") -> pd.DataFrame:
    toks = [w for t in corpus_df[column] for w in t.split() if len(w) > 2]
    c = Counter(toks)
    total = sum(c.values())
    df = pd.DataFrame(c.most_common(), columns=["term", "count"])
    df["relative_per_10k"] = (df["count"] / total * 10_000).round(2)
    df["n_sentences"] = df.term.map(
        Counter(w for t in corpus_df[column] for w in set(t.split())))
    return df


def compute_tfidf(corpus_df: pd.DataFrame, group_col: str = "level2", top_n: int = 15,
                  min_df: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """TF-IDF where each section (group_col) is one document. Returns
    (top terms per section, global ranking by max TF-IDF)."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    docs = corpus_df.groupby(["chapter", group_col], sort=False).lemma_text.apply(" ".join).reset_index()
    docs = docs[docs.lemma_text.str.split().str.len() >= 30]
    vec = TfidfVectorizer(min_df=min_df, token_pattern=r"(?u)\b[^\s\d]{3,}\b", sublinear_tf=True)
    X = vec.fit_transform(docs.lemma_text)
    terms = np.array(vec.get_feature_names_out())
    rows = []
    for i, (_, r) in enumerate(docs.iterrows()):
        row = X[i].toarray().ravel()
        for j in row.argsort()[::-1][:top_n]:
            if row[j] > 0:
                rows.append({"chapter": r.chapter, "section": r[group_col], "term": terms[j],
                             "tfidf": round(float(row[j]), 4)})
    per_section = pd.DataFrame(rows)
    glob = pd.DataFrame({"term": terms, "max_tfidf": X.max(axis=0).toarray().ravel(),
                         "mean_tfidf": np.asarray(X.mean(axis=0)).ravel()})
    glob = glob.sort_values("mean_tfidf", ascending=False).round(4)
    return per_section, glob


def compute_ngrams(corpus_df: pd.DataFrame, n: int = 2, column: str = "lemma_text",
                   min_count: int = 2) -> pd.DataFrame:
    """N-grams within sentences over stopword-free lemma text (so they do not
    cross sentence boundaries)."""
    c = Counter()
    for t in corpus_df[column]:
        toks = [w for w in t.split()]
        c.update(" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1))
    df = pd.DataFrame([(k, v) for k, v in c.items() if v >= min_count], columns=["ngram", "count"])
    return df.sort_values("count", ascending=False).reset_index(drop=True)


def words_per_section(paragraphs_df: pd.DataFrame) -> pd.DataFrame:
    p = paragraphs_df[paragraphs_df.block_type.isin(["body", "list_item", "subheading", "footnote",
                                                     "caption", "quote"])]
    return (p.groupby(["chapter", "level2"], sort=False)
            .agg(page_start=("page", "min"), page_end=("page_end", "max"), words=("n_words", "sum"),
                 paragraphs=("paragraph_id", "count")).reset_index())


# --- Framing / causal / sentiment ---------------------------------------------------

def _modal_count(doc) -> int:
    n = 0
    toks = list(doc)
    for i, t in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        nxt2 = toks[i + 2] if i + 2 < len(toks) else None
        if t.lemma_ in ("deber", "poder") and nxt is not None and "Inf" in nxt.morph.get("VerbForm"):
            n += 1
        elif t.lemma_ in ("tener", "haber") and nxt is not None and nxt.lower_ == "que" and nxt2 is not None \
                and "Inf" in nxt2.morph.get("VerbForm"):
            n += 1
    return n


def framing_features(corpus_df: pd.DataFrame, nlp=None) -> pd.DataFrame:
    """Per-sentence lexicon hits: certainty, hedging, attribution, adversarial,
    thematic frames, causal markers (core/extended), modal constructions,
    positive/negative evaluative terms."""
    if nlp is None:
        from src.preprocess import get_nlp
        nlp = get_nlp()
    rx = {
        "certainty": _phrase_regex(lx.CERTAINTY),
        "hedging": _phrase_regex(lx.HEDGING),
        "attribution": _phrase_regex(lx.ATTRIBUTION),
        "adversarial": _phrase_regex(lx.ADVERSARIAL),
        "causal_core": _phrase_regex(lx.CAUSAL_MARKERS_CORE),
        "causal_extended": _phrase_regex(lx.CAUSAL_MARKERS_EXTENDED),
        "positive": _phrase_regex(lx.POSITIVE),
        "negative": _phrase_regex(lx.NEGATIVE),
    }
    frame_rx = {k: _phrase_regex(v) for k, v in lx.FRAMES.items()}
    rows = []
    for (_, r), doc in zip(corpus_df.iterrows(), nlp.pipe(corpus_df.clean_text, batch_size=64)):
        low = r.clean_text.lower()
        row = {"sentence_id": r.sentence_id, "page": r.page, "chapter": r.chapter, "level2": r.level2,
               "n_words": len(words(r.clean_text))}
        for k, pat in rx.items():
            hits = pat.findall(low)
            row[f"{k}_n"] = len(hits)
            row[f"{k}_terms"] = "; ".join(hits)
        for k, pat in frame_rx.items():
            row[f"frame_{k}_n"] = len(pat.findall(low))
        row["modal_n"] = _modal_count(doc)
        row["first_person_plural_n"] = sum(1 for t in doc if "Person=1" in str(t.morph) and "Number=Plur" in str(t.morph))
        rows.append(row)
    return pd.DataFrame(rows)


def exploratory_sentiment(corpus_df: pd.DataFrame) -> pd.DataFrame:
    """Two exploratory signals, reported side by side and never merged:

    1. `lexicon_polarity` = (pos - neg) / (pos + neg) from src/lexicons.py.
    2. `model_score` from the `sentiment-analysis-spanish` package (a Naive
       Bayes classifier trained on Spanish product/film reviews; 0 = negative,
       1 = positive). Strong domain mismatch with institutional prose — see
       documents/methodology.md. Left NaN if the package is unavailable.
    """
    pos_rx, neg_rx = _phrase_regex(lx.POSITIVE), _phrase_regex(lx.NEGATIVE)
    out = corpus_df[["sentence_id", "page", "chapter", "level2"]].copy()
    pos = corpus_df.clean_text.str.lower().map(lambda t: len(pos_rx.findall(t)))
    neg = corpus_df.clean_text.str.lower().map(lambda t: len(neg_rx.findall(t)))
    out["lexicon_pos"], out["lexicon_neg"] = pos, neg
    out["lexicon_polarity"] = np.where(pos + neg > 0, (pos - neg) / (pos + neg).replace(0, 1), np.nan)
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from sentiment_analysis_spanish import sentiment_analysis

            model = sentiment_analysis.SentimentAnalysisSpanish()
            out["model_score"] = corpus_df.clean_text.map(lambda t: round(float(model.sentiment(t)), 4))
    except Exception:  # pragma: no cover
        out["model_score"] = np.nan
    return out


def tag_causal_language(corpus_df: pd.DataFrame) -> pd.DataFrame:
    """Sentences containing causal markers, for the dedicated causal-claims
    review table. Tagging does NOT imply the causal claim is right or wrong."""
    core, ext = _phrase_regex(lx.CAUSAL_MARKERS_CORE), _phrase_regex(lx.CAUSAL_MARKERS_EXTENDED)
    actor_rx = re.compile(r"\b(gobierno|administraci[oó]n|régimen|ministeri[oa]|ministr[oa]|presidente|petro|"
                          r"gerente|director|funcionari[oa]s?|entidad)\b", re.I)
    rows = []
    for _, r in corpus_df.iterrows():
        low = r.clean_text.lower()
        c_hits, e_hits = core.findall(low), ext.findall(low)
        if not (c_hits or e_hits):
            continue
        rows.append({
            "sentence_id": r.sentence_id, "paragraph_id": r.paragraph_id, "page": r.page,
            "section": r.section, "marker_core": "; ".join(c_hits), "marker_extended": "; ".join(e_hits),
            "marker_set": "core" if c_hits else "extended_only",
            "mentions_actor": bool(actor_rx.search(r.clean_text)),
            "actor_terms": "; ".join(sorted({m.lower() for m in actor_rx.findall(r.clean_text)})),
            "has_number": r.numbers != "[]",
            "text": r.clean_text,
            "review_status": "pending_human_review",
            "review_note": "",
        })
    return pd.DataFrame(rows)
