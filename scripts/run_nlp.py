#!/usr/bin/env python3
"""Exploratory NLP over the corpus. Writes tables to outputs/tables/ and
network exports to outputs/networks/. All outputs are descriptive.

Usage:
    python scripts/run_nlp.py [--skip-topics] [--skip-sentiment]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import embeddings as emb_mod
from src import entities as ent
from src import nlp
from src import topics as tp
from src.config import INTERIM_DIR, NETWORKS_DIR, PAGES_JSONL_PATH, TABLES_DIR
from src.corpus import analytic, load_corpus, load_paragraphs
from src.preprocess import get_nlp


def w(df: pd.DataFrame, name: str) -> None:
    df.to_csv(TABLES_DIR / name, index=False)
    print(f"  wrote outputs/tables/{name} ({len(df)} rows)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-topics", action="store_true")
    ap.add_argument("--skip-sentiment", action="store_true")
    args = ap.parse_args()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    NETWORKS_DIR.mkdir(parents=True, exist_ok=True)

    corpus_all = load_corpus()
    paragraphs = load_paragraphs()
    corpus = analytic(corpus_all)  # document prose, OCR excluded
    n_pages = sum(1 for _ in open(PAGES_JSONL_PATH, encoding="utf-8"))
    spacy_nlp = get_nlp()
    print(f"[nlp] analytic sentences={len(corpus)} (of {len(corpus_all)})")

    # 1. Basic stats / frequencies / TF-IDF / n-grams --------------------------------
    stats = nlp.compute_basic_stats(corpus, paragraphs, n_pages)
    stats["spacy_model"] = spacy_nlp.meta["name"] + "-" + spacy_nlp.meta["version"]
    (TABLES_DIR / "corpus_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n")
    w(pd.DataFrame(list(stats.items()), columns=["metric", "value"]), "corpus_stats.csv")
    w(nlp.words_per_section(paragraphs), "words_per_section.csv")
    w(nlp.compute_term_frequencies(corpus).head(1000), "term_frequencies.csv")
    per_sec, glob = nlp.compute_tfidf(corpus)
    w(per_sec, "tfidf_by_section.csv")
    w(glob.head(500), "tfidf_global.csv")
    w(nlp.compute_ngrams(corpus, 2).head(500), "bigrams.csv")
    w(nlp.compute_ngrams(corpus, 3).head(500), "trigrams.csv")

    # 2. Entities + networks -----------------------------------------------------------
    mentions = ent.extract_entity_mentions(corpus, spacy_nlp)
    aliases = ent.find_acronym_definitions(corpus.clean_text.tolist())
    mentions, merges = ent.normalise_aliases(mentions, aliases)
    w(aliases, "entity_acronym_definitions.csv")
    w(merges, "entity_aliases.csv")
    w(mentions, "entity_mentions.csv")
    entities = ent.summarise_entities(mentions)
    w(entities, "entities.csv")

    G = ent.build_entity_cooccurrence_network(mentions)
    ent.save_graph(G, NETWORKS_DIR / "entity_network.graphml", NETWORKS_DIR / "entity_network.json")
    print(f"  entity network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    concept_terms = glob.sort_values("mean_tfidf", ascending=False).term.head(80).tolist()
    C = ent.build_concept_network(corpus, concept_terms)
    ent.save_graph(C, NETWORKS_DIR / "concept_network.graphml", NETWORKS_DIR / "concept_network.json")
    print(f"  concept network: {C.number_of_nodes()} nodes, {C.number_of_edges()} edges")

    # 3. Framing / causal / sentiment --------------------------------------------------
    fr = nlp.framing_features(corpus, spacy_nlp)
    w(fr, "framing_sentences.csv")
    num_cols = [c for c in fr.columns if c.endswith("_n") and c != "n_words"]
    by_ch = fr.groupby("chapter")[num_cols + ["n_words"]].sum()
    rates = (by_ch[num_cols].div(by_ch["n_words"], axis=0) * 1000).round(2)
    rates.columns = [c.replace("_n", "_per_1k_words") for c in rates.columns]
    w(rates.reset_index().merge(by_ch[["n_words"]].reset_index(), on="chapter"), "framing_by_chapter.csv")
    w(nlp.tag_causal_language(corpus), "causal_sentences.csv")
    if not args.skip_sentiment:
        s = nlp.exploratory_sentiment(corpus)
        w(s, "sentiment_sentences.csv")
        agg = s.groupby("chapter").agg(sentences=("sentence_id", "count"),
                                       lexicon_pos=("lexicon_pos", "sum"), lexicon_neg=("lexicon_neg", "sum"),
                                       mean_model_score=("model_score", "mean")).reset_index()
        agg["lexicon_neg_share"] = (agg.lexicon_neg / (agg.lexicon_pos + agg.lexicon_neg)).round(3)
        agg["model_lexicon_spearman"] = np.nan
        valid = s.dropna(subset=["lexicon_polarity", "model_score"])
        if len(valid) > 10:
            agg["model_lexicon_spearman"] = round(valid.lexicon_polarity.corr(valid.model_score, method="spearman"), 3)
        w(agg.round(3), "sentiment_by_chapter.csv")

    # 4. Embeddings + topics ------------------------------------------------------------
    paras = emb_mod.paragraph_table(corpus)
    E, method = emb_mod.embed_paragraphs(paras)
    np.save(INTERIM_DIR / "paragraph_embeddings.npy", E)
    (TABLES_DIR / "embedding_method.txt").write_text(method + "\n")
    print(f"  embeddings: {E.shape} via {method}")
    keys, S = emb_mod.embed_sections(paras, E)
    sim = pd.DataFrame(emb_mod.cosine_similarity_matrix(S).round(4),
                       index=keys.level2, columns=keys.level2)
    sim.insert(0, "chapter", keys.chapter.values)
    sim.to_csv(TABLES_DIR / "section_similarity.csv")

    if args.skip_topics:
        return
    docs = paras.lemma_text.tolist()
    texts = [d.split() for d in docs]
    sweep = tp.k_sweep(docs, texts)
    w(sweep, "topic_k_sweep.csv")
    k = int(sweep[sweep.model == "tfidf_nmf"].sort_values("npmi", ascending=False).k.iloc[0])
    print(f"  chosen k={k} (best NMF NPMI); same k used for LDA and clustering for comparability")

    all_summary, all_examples, all_doc = [], [], []
    m, W, vocab = tp.fit_tfidf_nmf(docs, k)
    s_, e_, d_ = tp.summarise_model("tfidf_nmf", W, m.components_, vocab, paras)
    all_summary += s_; all_examples += e_; all_doc.append(d_)
    m, W, vocab = tp.fit_lda(docs, k)
    s_, e_, d_ = tp.summarise_model("lda", W, m.components_, vocab, paras)
    all_summary += s_; all_examples += e_; all_doc.append(d_)
    km, W, vocab, ctfidf = tp.fit_embedding_clusters(docs, E, k)
    s_, e_, d_ = tp.summarise_model("embedding_kmeans", W, ctfidf, vocab, paras)
    all_summary += s_; all_examples += e_; all_doc.append(d_)

    try:
        tp.fit_bertopic(paras.text.tolist())
        bertopic_status = "run"
    except Exception as exc:
        bertopic_status = f"not run: {type(exc).__name__}: {str(exc)[:160]}"
    print(f"  BERTopic: {bertopic_status}")

    summary = pd.DataFrame(all_summary)
    summary["npmi_model"] = summary.model.map(
        {"tfidf_nmf": sweep.query("model=='tfidf_nmf' and k==@k").npmi.iloc[0],
         "lda": sweep.query("model=='lda' and k==@k").npmi.iloc[0]})
    w(summary, "topics_summary.csv")
    w(pd.DataFrame(all_examples), "topic_examples.csv")
    doc_topics = pd.concat(all_doc)
    w(doc_topics, "doc_topics.csv")
    w(tp.topics_by_section(doc_topics, paras), "topics_by_chapter.csv")
    w(tp.model_agreement(doc_topics), "topic_model_agreement.csv")
    (TABLES_DIR / "topic_models_status.json").write_text(json.dumps(
        {"k": k, "embedding_method": method, "bertopic": bertopic_status,
         "n_paragraphs_modelled": len(paras)}, indent=2) + "\n")

    xy = emb_mod.project_umap(E)
    emap = paras[["paragraph_id", "page", "chapter", "level2"]].copy()
    emap["x"], emap["y"] = xy[:, 0].round(4), xy[:, 1].round(4)
    dt = doc_topics.pivot(index="paragraph_id", columns="model", values="dominant_topic")
    emap = emap.merge(dt, left_on="paragraph_id", right_index=True, how="left")
    emap["excerpt"] = paras.text.str[:200].values
    w(emap, "embedding_map.csv")


if __name__ == "__main__":
    main()
