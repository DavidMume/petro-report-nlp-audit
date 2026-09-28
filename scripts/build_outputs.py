#!/usr/bin/env python3
"""Regenerate every chart in outputs/charts/ and the provenance manifest
outputs/data_manifest.json from the processed tables.

Usage:
    python scripts/build_outputs.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import visualisations as v
from src.config import (CHARTS_DIR, DATA_MANIFEST_PATH, NETWORKS_DIR, PAGES_JSONL_PATH, PROCESSED_DIR, ROOT_DIR,
                        SOURCE_METADATA_PATH, SOURCES_DIR, TABLES_DIR)
from src.corpus import analytic, load_corpus, load_paragraphs
from src.extract import compute_sha256

T = TABLES_DIR

PRODUCERS = {
    "pages.jsonl": "scripts/extract_document.py", "extraction_log.csv": "scripts/extract_document.py",
    "corpus": "scripts/build_corpus.py", "paragraphs": "scripts/build_corpus.py", "sections.csv": "scripts/build_corpus.py",
    "removed_headers_footers.csv": "scripts/build_corpus.py",
    "claims.csv": "scripts/extract_claims.py", "numeric_claims.csv": "scripts/extract_claims.py + scripts/validate_claims.py",
    "causal_claims_review.csv": "scripts/extract_claims.py",
    "claim_evidence.csv": "curated (manual) — validated by scripts/validate_claims.py",
    "claim_assessments.csv": "curated (manual) — validated by scripts/validate_claims.py",
    "claims_with_assessments.csv": "scripts/validate_claims.py", "verification_coverage.csv": "scripts/validate_claims.py",
    "source_triangulation.csv": "curated (manual)", "evidence_ledger.csv": "curated (manual)",
    "source_registry.csv": "curated (manual)", "numeric_reconstructions.csv": "curated (manual)",
    "stylometry": "scripts/run_authorship.py", "ai_detector_status.json": "scripts/run_authorship.py",
    "provenance_statements.csv": "scripts/run_authorship.py",
    "chart_": "scripts/build_outputs.py",
}


def producer(name: str) -> str:
    for k, s in PRODUCERS.items():
        if name.startswith(k) or name == k:
            return s
    return "scripts/run_nlp.py"


def build_data_manifest() -> dict:
    meta = json.loads(SOURCE_METADATA_PATH.read_text(encoding="utf-8"))
    files = sorted(list(PROCESSED_DIR.glob("*.csv")) + list(PROCESSED_DIR.glob("*.parquet")) + list(T.glob("*.csv"))
                   + list(T.glob("*.json")) + list(SOURCES_DIR.glob("*.csv")) + [PAGES_JSONL_PATH])
    rows = []
    for f in files:
        if not f.exists():
            continue
        entry = {"filename": str(f.relative_to(ROOT_DIR)), "sha256": compute_sha256(f),
                 "processing_script": producer(f.name), "rows": None, "columns": None}
        if f.suffix == ".csv":
            try:
                df = pd.read_csv(f, low_memory=False)
                entry["rows"], entry["columns"] = int(len(df)), list(df.columns)
            except pd.errors.EmptyDataError:
                entry["rows"], entry["columns"] = 0, []
        elif f.suffix == ".parquet":
            df = pd.read_parquet(f)
            entry["rows"], entry["columns"] = int(len(df)), list(df.columns)
        if f.parent == SOURCES_DIR or "curated" in entry["processing_script"]:
            entry["source"] = "curated from external sources listed in sources/evidence_ledger.csv (access dates there)"
            entry["download_date"] = None
        else:
            entry["source"] = f"derived from data/raw/{meta['filename']} (sha256 {meta['sha256']})"
            entry["download_date"] = meta.get("download_date")
        rows.append(entry)
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_document": {k: meta.get(k) for k in ("title", "filename", "sha256", "pages", "download_date")},
            "datasets": rows}


def chapter_tfidf(corpus: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer

    docs = corpus.groupby("chapter", sort=False).lemma_text.apply(" ".join)
    vec = TfidfVectorizer(min_df=1, token_pattern=r"(?u)\b[^\s\d]{3,}\b", sublinear_tf=True)
    X = vec.fit_transform(docs.values)
    terms = np.array(vec.get_feature_names_out())
    rows = []
    for i, ch in enumerate(docs.index):
        r = X[i].toarray().ravel()
        for j in r.argsort()[::-1][:top_n]:
            rows.append({"chapter": ch, "term": terms[j], "tfidf": round(float(r[j]), 4)})
    return pd.DataFrame(rows)


def main() -> None:
    v.setup_style()
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    C = lambda name: CHARTS_DIR / f"{name}.png"  # noqa: E731

    corpus = analytic(load_corpus())
    paragraphs = load_paragraphs()
    n_pages = sum(1 for _ in open(PAGES_JSONL_PATH, encoding="utf-8"))
    claims = pd.read_csv(PROCESSED_DIR / "claims.csv")
    assess = pd.read_csv(PROCESSED_DIR / "claim_assessments.csv")
    merged = pd.read_csv(T / "claims_with_assessments.csv")
    ledger = pd.read_csv(SOURCES_DIR / "evidence_ledger.csv")
    numeric = pd.read_csv(PROCESSED_DIR / "numeric_claims.csv")
    segs = pd.read_csv(PROCESSED_DIR / "stylometry_segments.csv")
    feats = pd.read_csv(T / "stylometry_features.csv")
    scores = pd.read_csv(T / "stylometry_segment_scores.csv")

    v.plot_document_overview(paragraphs, n_pages, C("01_document_overview"))
    v.plot_words_per_section(pd.read_csv(T / "words_per_section.csv"), C("02_words_per_section"))
    v.plot_top_terms(pd.read_csv(T / "term_frequencies.csv"), C("03_top_terms"))
    ct = chapter_tfidf(corpus)
    ct.to_csv(T / "tfidf_by_chapter.csv", index=False)
    v.plot_tfidf_terms(ct, C("04_tfidf_terms"))
    v.plot_ngrams(pd.read_csv(T / "bigrams.csv"), C("05_top_bigrams"), 2)
    v.plot_ngrams(pd.read_csv(T / "trigrams.csv"), C("06_top_trigrams"), 3)
    v.plot_entity_frequencies(pd.read_csv(T / "entities.csv"), C("07_entity_frequencies"))
    v.plot_network(json.loads((NETWORKS_DIR / "entity_network.json").read_text()), C("08_entity_cooccurrence_network"),
                   "Red de coaparición de entidades (mismo párrafo)")
    v.plot_network(json.loads((NETWORKS_DIR / "concept_network.json").read_text()), C("08b_concept_network"),
                   "Red de conceptos (coaparición de lemas en la misma oración)", top_n=40, label_n=25, color_by=None)
    summary = pd.read_csv(T / "topics_summary.csv")
    v.plot_topic_distribution(summary, C("09_topic_distribution"))
    v.plot_topics_by_section(pd.read_csv(T / "topics_by_chapter.csv"), summary, C("10_topics_by_section"))
    v.plot_semantic_embedding_map(pd.read_csv(T / "embedding_map.csv"),
                                  (T / "embedding_method.txt").read_text().strip(), C("11_semantic_embedding_map"))
    v.plot_claim_categories(claims, C("12_claim_categories"))
    v.plot_claims_by_section(claims, C("13_claims_by_section"))
    v.plot_verification_status_distribution(assess, int((merged.verification_status == "unassessed").sum()),
                                            C("14_verification_status_distribution"))
    v.plot_verification_status_by_claim_type(merged, C("15_verification_status_by_claim_type"))
    v.plot_sources_cited_by_report(claims, C("16_sources_cited_by_report")).to_csv(T / "sources_cited_by_report.csv", index=False)
    v.plot_sources_used_by_audit(ledger, C("17_sources_used_by_audit"))
    v.plot_timeline_of_claims(claims, C("18_timeline_of_claims")).to_csv(T / "claim_years.csv", index=False)
    v.plot_numeric_claims_dashboard(numeric, C("19_numeric_claims_dashboard"))
    fbc = pd.read_csv(T / "framing_by_chapter.csv")
    v.plot_causal_language(pd.read_csv(T / "causal_sentences.csv"), fbc, C("20_causal_language_analysis"))
    v.plot_framing_by_chapter(fbc, C("21_framing_by_chapter"))
    heat_cols = ["avg_sentence_length", "sentence_length_cv", "avg_word_length", "mattr_100", "hapax_ratio",
                 "lexical_density", "mean_dependency_depth", "fernandez_huerta", "first_person_per_1k", "passive_per_1k",
                 "connectors_per_1k", "hedging_per_1k", "certainty_per_1k", "numbers_per_1k", "semantic_continuity",
                 "pattern_no_x_sino_y_per_1k", "pattern_triad_list_per_1k", "pattern_headline_colon_per_1k",
                 "pattern_stock_phrases_per_1k", "punct_colon_per_1k_chars", "punct_semicolon_per_1k_chars"]
    v.plot_stylometry_heatmap(feats, segs, C("22_stylometry_heatmap"), heat_cols)
    v.plot_similarity_matrix(pd.read_csv(T / "stylometry_similarity_cosine.csv", index_col=0), segs,
                             C("23_stylometry_similarity_matrix"), "Similitud estilométrica entre segmentos (coseno)")
    v.plot_change_points(scores, pd.read_csv(T / "stylometry_change_points.csv"), C("24_stylometry_change_points"))
    v.plot_stylometry_pca(scores, pd.read_csv(T / "stylometry_pca_variance.csv"), C("25_stylometry_pca_map"))
    v.plot_sentiment(pd.read_csv(T / "sentiment_by_chapter.csv"), C("26_sentiment_exploratory"))

    manifest = build_data_manifest()
    manifest["charts"] = sorted(p.name for p in CHARTS_DIR.glob("*.png"))
    DATA_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[outputs] {len(manifest['charts'])} charts; manifest with {len(manifest['datasets'])} datasets")


if __name__ == "__main__":
    main()
