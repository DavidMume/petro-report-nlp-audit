"""Linguistic provenance / stylometry module (EXPLORATORY; RQ6, RQ7).

What this module does
---------------------
- Splits the document into comparable segments (~500-1000 words, never
  crossing a chapter boundary).
- Computes per-segment stylometric features.
- Compares segments (cosine similarity, Jensen-Shannon divergence of
  function-word distributions, Mahalanobis distance from the document
  centroid in PCA space, change-point detection along the document,
  clustering) and flags *locations* of stylistic change.
- Counts "LLM-associated" surface patterns, reported strictly as
  linguistic patterns.

What it does NOT do
-------------------
- It does not say who or what wrote any segment. A stylistic shift can come
  from different authors, editors, source material, section genre (e.g.
  per-minister sectoral chapters), copy-editing, quotations or technical
  vocabulary (methodology §23.3).
- It runs no AI detector: `apply_calibrated_detector` refuses to run until
  a Spanish-language calibration experiment (§23.5) has produced metrics.

Allowed conclusion phrasing (§32):
    "Estos segmentos presentan diferencias estilísticas respecto al resto del documento."
    "El clasificador X marcó estos segmentos como compatibles con generación mediante LLM."
    "El detector presentó una tasa de falsos positivos de X en nuestro corpus de control."
    "No existe evidencia suficiente para atribuir estos segmentos de manera concluyente a una herramienta de IA."
Disallowed: "ChatGPT escribió esta página." / "El informe fue escrito en un 67% por IA."
"""

from __future__ import annotations

import re
from collections import Counter

import numpy as np
import pandas as pd

from src import lexicons as lx
from src.config import STYLOMETRY_SEGMENTS_SCHEMA

SEGMENT_WORD_COUNT_RANGE = (500, 1000)
TARGET_WORDS = 700

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")

# 60 high-frequency Spanish function words (closed class), fixed in advance.
FUNCTION_WORDS = [
    "de", "la", "que", "el", "en", "y", "a", "los", "se", "del", "las", "un", "por", "con", "no",
    "una", "su", "para", "es", "al", "lo", "como", "más", "o", "pero", "sus", "le", "ha", "me", "si",
    "sin", "sobre", "este", "ya", "entre", "cuando", "todo", "esta", "ser", "son", "dos", "también",
    "fue", "había", "era", "muy", "hasta", "desde", "está", "mi", "porque", "qué", "sólo", "solo",
    "han", "yo", "hay", "vez", "puede", "todos",
]
CONNECTORS = [
    "además", "sin embargo", "por lo tanto", "por tanto", "en consecuencia", "asimismo", "no obstante",
    "por otra parte", "de igual forma", "de igual manera", "en este sentido", "por ello", "por eso",
    "es decir", "en efecto", "finalmente", "en suma", "en síntesis", "por su parte", "a su vez",
    "en particular", "en otras palabras", "así mismo", "igualmente", "de hecho", "mientras tanto",
]
# Surface patterns often associated with LLM-assisted prose in informal
# discussion. Reported as linguistic patterns only (§23.9).
LLM_ASSOCIATED_PATTERNS = {
    "no_x_sino_y": r"\bno (?:es|fue|son|era|solo|sólo|se trata de)\b[^.;]{1,80}?,? sino\b",
    "no_solo_sino": r"\bno solo\b[^.;]{1,80}\bsino (?:también|que)\b",
    "headline_colon": r"^[^.:]{3,70}:\s+[a-záéíóúñ]",
    "em_dash": r"—",
    "triad_list": r"\b\w+(?:\s\w+)?, \w+(?:\s\w+)? y \w+(?:\s\w+)?\b",
    "stock_phrases": r"\b(?:es importante (?:destacar|señalar|resaltar)|cabe (?:destacar|resaltar|señalar)|"
                     r"en este sentido|en síntesis|en suma|dicho de otro modo|en última instancia|"
                     r"juega un papel|pone de manifiesto|no es un hecho aislado)\b",
}

POS_TAGS = ["NOUN", "VERB", "ADJ", "ADV", "PROPN", "ADP", "DET", "PRON", "AUX", "CCONJ", "SCONJ", "NUM"]


def build_empty_segments_table() -> pd.DataFrame:
    return pd.DataFrame(columns=STYLOMETRY_SEGMENTS_SCHEMA)


# --- Segmentation -------------------------------------------------------------------

def segment_document(corpus_df: pd.DataFrame, target_words: int = TARGET_WORDS,
                     min_words: int = SEGMENT_WORD_COUNT_RANGE[0]) -> pd.DataFrame:
    """Consecutive sentences grouped into segments of ~target_words, never
    crossing a chapter boundary. A chapter remainder shorter than min_words
    is merged into the previous segment of the same chapter; a whole chapter
    shorter than min_words is kept and flagged `short_segment`."""
    segs = []
    for chapter, grp in corpus_df.groupby("chapter", sort=False):
        cur, words = [], 0
        chapter_segs = []
        for _, r in grp.iterrows():
            cur.append(r)
            words += len(WORD_RE.findall(r.clean_text))
            if words >= target_words:
                chapter_segs.append(cur)
                cur, words = [], 0
        if cur:
            if chapter_segs and words < min_words:
                chapter_segs[-1].extend(cur)
            else:
                chapter_segs.append(cur)
        segs.extend(chapter_segs)
    rows = []
    for i, rs in enumerate(segs, start=1):
        text = " ".join(r.clean_text for r in rs)
        pages = sorted({int(r.page) for r in rs})
        wc = len(WORD_RE.findall(text))
        rows.append({
            "segment_id": f"G{i:03d}",
            "pages": f"{pages[0]}-{pages[-1]}" if len(pages) > 1 else str(pages[0]),
            "page_start": pages[0],
            "section": rs[0].level2,
            "chapter": rs[0].chapter,
            "word_count": wc,
            "n_sentences": len(rs),
            "paragraph_ids": ";".join(dict.fromkeys(r.paragraph_id for r in rs)),
            "raw_text": text,
            "short_segment": wc < min_words,
        })
    return pd.DataFrame(rows)


# --- Features ------------------------------------------------------------------------

_VOWELS = "aeiouáéíóúü"
_STRONG = set("aeoáéíóú")


def count_syllables_es(word: str) -> int:
    """Approximate Spanish syllable count: vowel groups, split where two
    strong vowels meet (hiatus). Adequate for readability indices, not exact."""
    w = word.lower()
    n, prev_vowel, prev_strong = 0, False, False
    for ch in w:
        if ch in _VOWELS:
            strong = ch in _STRONG
            if not prev_vowel or (strong and prev_strong):
                n += 1
            prev_vowel, prev_strong = True, strong
        else:
            prev_vowel, prev_strong = False, False
    return max(n, 1)


def _mattr(tokens: list[str], window: int = 100) -> float:
    if len(tokens) <= window:
        return len(set(tokens)) / max(len(tokens), 1)
    return float(np.mean([len(set(tokens[i:i + window])) / window for i in range(0, len(tokens) - window + 1, 10)]))


def _depth(tok) -> int:
    # spaCy creates a new Token object on each access, so compare indices, not identity.
    d = 0
    while tok.head.i != tok.i and d < 200:
        tok = tok.head
        d += 1
    return d


def _count(patterns: list[str], text: str) -> int:
    low = text.lower()
    return sum(len(re.findall(rf"(?<![\wáéíóúñ]){re.escape(p)}(?![\wáéíóúñ])", low)) for p in patterns)


def compute_stylometric_features(segments_df: pd.DataFrame, paragraphs_df: pd.DataFrame | None = None,
                                 nlp=None) -> pd.DataFrame:
    """Per-segment stylometric features (see module docstring)."""
    if nlp is None:
        from src.preprocess import get_nlp
        nlp = get_nlp()
    para_len = {}
    if paragraphs_df is not None:
        para_len = dict(zip(paragraphs_df.paragraph_id, paragraphs_df.n_words))
    rows = []
    for (_, s), doc in zip(segments_df.iterrows(), nlp.pipe(segments_df.raw_text, batch_size=8)):
        toks = [t for t in doc if not t.is_space]
        words = [t.text.lower() for t in toks if any(c.isalpha() for c in t.text)]
        nw = max(len(words), 1)
        sents = list(doc.sents)
        slen = np.array([sum(1 for t in s_ if any(c.isalpha() for c in t.text)) for s_ in sents])
        wlen = np.array([len(w) for w in words])
        c = Counter(words)
        syll = sum(count_syllables_es(w) for w in words)
        pos = Counter(t.pos_ for t in toks if not t.is_punct)
        n_pos = max(sum(pos.values()), 1)
        depths = [max((_depth(t) for t in s_), default=0) for s_ in sents]
        text = s.raw_text
        low = text.lower()
        chars = max(len(text), 1)
        vecs = [s_.vector for s_ in sents if s_.vector_norm > 0]
        if len(vecs) > 1:
            v = np.array(vecs)
            v = v / np.linalg.norm(v, axis=1, keepdims=True)
            sem_cont = float(np.mean(np.sum(v[1:] * v[:-1], axis=1)))
        else:
            sem_cont = np.nan
        pids = s.paragraph_ids.split(";")
        pl = [para_len[p] for p in pids if p in para_len]
        row = {
            "segment_id": s.segment_id,
            "avg_sentence_length": round(float(slen.mean()), 3),
            "sentence_length_var": round(float(slen.var()), 3),
            "sentence_length_cv": round(float(slen.std() / slen.mean()), 4) if slen.mean() else np.nan,
            "avg_word_length": round(float(wlen.mean()), 4),
            "share_words_1_3": round(float((wlen <= 3).mean()), 4),
            "share_words_4_6": round(float(((wlen >= 4) & (wlen <= 6)).mean()), 4),
            "share_words_7_9": round(float(((wlen >= 7) & (wlen <= 9)).mean()), 4),
            "share_words_10p": round(float((wlen >= 10).mean()), 4),
            "type_token_ratio": round(len(c) / nw, 4),
            "mattr_100": round(_mattr(words, 100), 4),
            "hapax_ratio": round(sum(1 for v in c.values() if v == 1) / nw, 4),
            "avg_paragraph_length": round(float(np.mean(pl)), 2) if pl else np.nan,
            "lexical_density": round(sum(pos[p] for p in ("NOUN", "VERB", "ADJ", "ADV", "PROPN")) / n_pos, 4),
            "stopword_ratio": round(sum(1 for t in toks if t.is_stop) / max(len(toks), 1), 4),
            "mean_dependency_depth": round(float(np.mean(depths)), 3) if depths else np.nan,
            "max_dependency_depth": int(max(depths)) if depths else 0,
            "fernandez_huerta": round(206.84 - 0.60 * (syll / nw * 100) - 1.02 * (len(sents) / nw * 100), 2),
            "szigriszt_inflesz": round(206.835 - 62.3 * (syll / nw) - (nw / max(len(sents), 1)), 2),
            "first_person_per_1k": round(sum(1 for t in toks if "Person=1" in str(t.morph)) / nw * 1000, 3),
            "passive_per_1k": round(sum(1 for t in toks if t.dep_ in ("aux:pass", "nsubj:pass", "expl:pass")
                                        or (t.lemma_ == "ser" and t.head.morph.get("VerbForm") == ["Part"]))
                                    / nw * 1000, 3),
            "connectors_per_1k": round(_count(CONNECTORS, text) / nw * 1000, 3),
            "modal_per_1k": round(sum(1 for i, t in enumerate(toks[:-1]) if t.lemma_ in ("deber", "poder")
                                      and "Inf" in toks[i + 1].morph.get("VerbForm")) / nw * 1000, 3),
            "hedging_per_1k": round(_count(lx.HEDGING, text) / nw * 1000, 3),
            "certainty_per_1k": round(_count(lx.CERTAINTY, text) / nw * 1000, 3),
            "numbers_per_1k": round(sum(1 for t in toks if t.like_num) / nw * 1000, 3),
            "semantic_continuity": round(sem_cont, 4) if sem_cont == sem_cont else np.nan,
        }
        for p in POS_TAGS:
            row[f"pos_{p}"] = round(pos[p] / n_pos, 4)
        for mark, name in [(",", "comma"), (";", "semicolon"), (":", "colon"), ("(", "paren"),
                           ("—", "emdash"), ("«", "guillemet"), ("“", "curly_quote"), ("%", "percent")]:
            row[f"punct_{name}_per_1k_chars"] = round(text.count(mark) / chars * 1000, 3)
        for fw in FUNCTION_WORDS:
            row[f"fw_{fw}"] = round(c[fw] / nw, 5)
        for k, rx in LLM_ASSOCIATED_PATTERNS.items():
            flags = re.M if k == "headline_colon" else 0
            if k == "headline_colon":
                n = sum(1 for s_ in sents if re.match(rx, s_.text.strip()))
            else:
                n = len(re.findall(rx, low if k != "em_dash" else text, flags))
            row[f"pattern_{k}_per_1k"] = round(n / nw * 1000, 3)
        rows.append(row)
    return pd.DataFrame(rows)


# --- Internal consistency ------------------------------------------------------------------

def _js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    from scipy.spatial.distance import jensenshannon

    p = p + 1e-9
    q = q + 1e-9
    return float(jensenshannon(p / p.sum(), q / q.sum(), base=2) ** 2)


def core_feature_columns(features_df: pd.DataFrame) -> list[str]:
    return [c for c in features_df.columns if c != "segment_id" and not c.startswith("fw_")
            and not c.startswith("pattern_") and features_df[c].notna().all()]


def analyse_internal_consistency(features_df: pd.DataFrame, segments_df: pd.DataFrame,
                                 n_pcs: int = 8, random_state: int = 42) -> dict:
    """Pairwise similarity, JS divergence, Mahalanobis outliers, change points
    and clustering. Returns a dict of DataFrames. Flags are locations of
    stylistic difference only — no causal label is attached."""
    import ruptures as rpt
    from scipy.stats import chi2
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.covariance import LedoitWolf
    from sklearn.decomposition import PCA
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    from sklearn.preprocessing import StandardScaler

    cols = core_feature_columns(features_df)
    fw_cols = [c for c in features_df.columns if c.startswith("fw_")]
    X = StandardScaler().fit_transform(features_df[cols + fw_cols].values)
    ids = features_df.segment_id.tolist()

    Xn = X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)
    cos = pd.DataFrame(np.round(Xn @ Xn.T, 4), index=ids, columns=ids)

    F = features_df[fw_cols].values
    js = np.zeros((len(ids), len(ids)))
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            js[i, j] = js[j, i] = _js_divergence(F[i], F[j])
    jsd = pd.DataFrame(np.round(js, 5), index=ids, columns=ids)

    k = min(n_pcs, len(ids) - 2)
    pca = PCA(n_components=k, random_state=random_state)
    Z = pca.fit_transform(X)
    lw = LedoitWolf().fit(Z)
    md2 = lw.mahalanobis(Z)
    threshold = chi2.ppf(0.975, df=k)
    seg = segments_df.set_index("segment_id")
    outliers = pd.DataFrame({
        "segment_id": ids,
        "pages": [seg.loc[i, "pages"] for i in ids],
        "chapter": [seg.loc[i, "chapter"] for i in ids],
        "section": [seg.loc[i, "section"] for i in ids],
        "mahalanobis_sq": np.round(md2, 3),
        "chi2_975_threshold": round(float(threshold), 3),
        "flag_stylistic_outlier": md2 > threshold,
        "mean_js_to_others": np.round(js.sum(axis=1) / (len(ids) - 1), 5),
        "pc1": np.round(Z[:, 0], 4), "pc2": np.round(Z[:, 1], 4),
    })

    # Change points along document order on the first PCs. Run over a grid
    # of BIC-scaled penalties and two cost models (sensitivity analysis,
    # §25.1); a break is "robust" only if it appears in >= 2/3 of configurations.
    signal = Z[:, : min(4, k)]
    signal = (signal - signal.mean(axis=0)) / signal.std(axis=0)  # unit variance per PC
    d = signal.shape[1]
    configs = []
    for model in ("l2", "rbf"):
        base = d * np.log(len(ids)) if model == "l2" else np.log(len(ids))  # BIC-style scale per cost model
        for mult in (0.5, 1, 1.5, 2, 3, 4):
            pen = round(float(base * mult), 3)
            try:
                b = rpt.Pelt(model=model, min_size=3, jump=1).fit(signal).predict(pen=pen)  # jump=1: consider every position
            except Exception:
                continue
            configs.append((model, pen, [x for x in b if x < len(ids)]))
    counts = Counter(b for _, _, bs in configs for b in bs)
    cp_rows = []
    for b, n in sorted(counts.items()):
        cp_rows.append({"break_before_segment": ids[b], "pages": seg.loc[ids[b], "pages"],
                        "chapter": seg.loc[ids[b], "chapter"], "section": seg.loc[ids[b], "section"],
                        "coincides_with_chapter_boundary": seg.loc[ids[b], "chapter"] != seg.loc[ids[b - 1], "chapter"],
                        "n_configs_detected": n, "n_configs": len(configs),
                        "robust": n >= 2 * len(configs) / 3})
    cps = pd.DataFrame(cp_rows)
    sens = pd.DataFrame([{"cost_model": m, "penalty": p, "n_breaks": len(bs),
                          "breaks": ";".join(ids[b] for b in bs)} for m, p, bs in configs])

    # Clustering and its alignment with chapters (a structural baseline).
    chapters = [seg.loc[i, "chapter"] for i in ids]
    clus_rows = []
    best = None
    for n in range(2, 6):
        lab = AgglomerativeClustering(n_clusters=n, linkage="ward").fit_predict(Z)
        sil = silhouette_score(Z, lab)
        ari = adjusted_rand_score(chapters, lab)
        clus_rows.append({"n_clusters": n, "silhouette": round(float(sil), 4), "ari_vs_chapters": round(float(ari), 4)})
        if best is None or sil > best[0]:
            best = (sil, n, lab)
    outliers["style_cluster"] = best[2]
    pcs = pd.DataFrame({"component": [f"PC{i + 1}" for i in range(k)],
                        "explained_variance_ratio": np.round(pca.explained_variance_ratio_, 4)})
    loadings = pd.DataFrame(pca.components_[:3].T, index=cols + fw_cols, columns=["PC1", "PC2", "PC3"]).round(4)
    loadings["abs_pc1"] = loadings.PC1.abs()
    return {"cosine": cos, "js_divergence": jsd, "segment_scores": outliers, "change_points": cps,
            "change_point_sensitivity": sens,
            "clustering": pd.DataFrame(clus_rows), "pca_variance": pcs,
            "pca_loadings": loadings.sort_values("abs_pc1", ascending=False).head(25).reset_index(names="feature")}


# --- Detectors (gated) -----------------------------------------------------------------------

DETECTOR_STATUS = {
    "status": "not_run",
    "reason": ("No AI-text detector with convincing Spanish-language validation was available in the "
               "execution environment (huggingface.co blocked; no commercial detector APIs used), and the "
               "calibration corpora A (human, 2015-2021), B (AI-generated) and C (hybrid) required by "
               "methodology §23.5 have not been assembled. Per §23.4-23.6, no detector output is produced."),
    "next_step": "Assemble corpora A/B/C (see sources/calibration/README.md), then run run_detector_calibration_experiment().",
}


def run_detector_calibration_experiment(corpus_a_human, corpus_b_ai, corpus_c_hybrid, detector=None) -> dict:
    """Mandatory calibration before any detector is used on the report
    (§23.5): precision, recall, specificity, FPR, FNR, F1 and ROC-AUC on
    Spanish control corpora. `detector` is a callable text -> score in [0,1]."""
    if detector is None or not (len(corpus_a_human) and len(corpus_b_ai)):
        raise ValueError("Calibration needs a detector callable and non-empty corpora A and B.")
    from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

    texts = list(corpus_a_human) + list(corpus_b_ai) + list(corpus_c_hybrid)
    y = [0] * len(corpus_a_human) + [1] * len(corpus_b_ai) + [1] * len(corpus_c_hybrid)
    scores = [float(detector(t)) for t in texts]
    pred = [int(s >= 0.5) for s in scores]
    tn = sum(1 for a, b in zip(y, pred) if a == 0 and b == 0)
    fp = sum(1 for a, b in zip(y, pred) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y, pred) if a == 1 and b == 0)
    tp = sum(1 for a, b in zip(y, pred) if a == 1 and b == 1)
    return {"precision": precision_score(y, pred, zero_division=0), "recall": recall_score(y, pred, zero_division=0),
            "specificity": tn / max(tn + fp, 1), "false_positive_rate": fp / max(fp + tn, 1),
            "false_negative_rate": fn / max(fn + tp, 1), "f1": f1_score(y, pred, zero_division=0),
            "roc_auc": roc_auc_score(y, scores) if len(set(y)) > 1 else None, "n": len(y)}


def apply_calibrated_detector(segments_df: pd.DataFrame, detector_name: str,
                              calibration_metrics: dict) -> pd.DataFrame:
    """Refuses to run without calibration metrics for this detector."""
    if not calibration_metrics:
        raise ValueError(
            "Refusing to apply an uncalibrated detector. Run run_detector_calibration_experiment() first — "
            "see documents/methodology.md §23.5."
        )
    raise NotImplementedError("Wire a calibrated detector here once one exists (record detector, version, "
                              "date, segment, score, language, limitations).")
