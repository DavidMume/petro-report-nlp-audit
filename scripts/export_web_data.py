#!/usr/bin/env python3
"""Export the pipeline outputs as JSON for the web app (web/public/data/).
The web app only reads these files; it computes nothing on its own.

Usage:
    python scripts/export_web_data.py
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (DOCUMENTS_DIR, NETWORKS_DIR, PROCESSED_DIR, ROOT_DIR, SOURCE_METADATA_PATH, SOURCES_DIR,
                        TABLES_DIR)

OUT = ROOT_DIR / "web" / "public" / "data"
T = TABLES_DIR


def records(df: pd.DataFrame) -> list[dict]:
    df = df.replace({np.nan: None})
    return json.loads(df.to_json(orient="records", force_ascii=False))


def dump(name: str, obj) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  web/public/data/{name} ({(OUT / name).stat().st_size / 1024:.0f} KB)")


def main() -> None:
    meta = json.loads(SOURCE_METADATA_PATH.read_text(encoding="utf-8"))
    stats = json.loads((T / "corpus_stats.json").read_text())
    topics_status = json.loads((T / "topic_models_status.json").read_text())
    detector = json.loads((T / "ai_detector_status.json").read_text())
    paragraphs = pd.read_parquet(PROCESSED_DIR / "paragraphs.parquet")
    claims = pd.read_csv(T / "claims_with_assessments.csv")
    evidence = pd.read_csv(PROCESSED_DIR / "claim_evidence.csv")
    ledger = pd.read_csv(SOURCES_DIR / "evidence_ledger.csv")

    log = pd.read_csv(T / "extraction_log.csv")
    extraction = {
        "pymupdf_pages": int((log.extraction_method == "pymupdf").sum()),
        "ocr_pages": int(log.used_ocr.sum()),
        "ocr_page_numbers": log[log.used_ocr].page.astype(int).tolist(),
        "figure_ocr_pages": log[log.ocr_figures > 0].page.astype(int).tolist(),
        "removed_header_footer_lines": int(len(pd.read_csv(T / "removed_headers_footers.csv"))),
    }
    dump("meta.json", {
        "extraction": extraction,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": meta, "stats": stats, "topics": topics_status, "ai_detectors": detector,
        "embedding_method": (T / "embedding_method.txt").read_text().strip(),
        "coverage": records(pd.read_csv(T / "verification_coverage.csv")),
    })

    p = paragraphs[paragraphs.block_type != "page_ocr"]
    dump("paragraphs.json", records(p[["paragraph_id", "page", "page_end", "section", "chapter", "level2", "level3",
                                        "block_type", "is_ocr", "clean_text", "n_words"]]))
    dump("sections.json", records(pd.read_csv(T / "words_per_section.csv")))
    wpp = p[p.block_type != "heading"].groupby(["page", "chapter"]).n_words.sum().reset_index()
    dump("words_per_page.json", records(wpp))

    keep = ["claim_id", "claim_text", "short_quote", "page", "section", "chapter", "level2", "claim_type",
            "claim_kind", "priority", "extraction_score", "cues", "is_causal", "time_period", "numeric_value", "unit",
            "source_cited_in_report", "verifiable", "verification_status", "confidence", "reasoning_summary",
            "robustness", "context_flags", "components_checked", "components_unverified", "evidence_source_ids",
            "paragraph_id", "sentence_id", "subject", "predicate", "object"]
    dump("claims.json", records(claims[[c for c in keep if c in claims.columns]]))
    dump("evidence.json", records(evidence))
    dump("ledger.json", records(ledger))
    dump("numeric.json", {
        "reconstructions": records(pd.read_csv(SOURCES_DIR / "numeric_reconstructions.csv")),
        "triangulation": records(pd.read_csv(T / "source_triangulation.csv")),
    })

    ents = pd.read_csv(T / "entities.csv")
    ents = ents[~ents.entity_type.isin(["GENERIC", "MISC"])].head(250)
    dump("entities.json", records(ents[["entity", "entity_type", "count", "pages", "n_paragraphs",
                                         "is_public_institution", "surface_forms"]]))
    for n in ("entity_network.json", "concept_network.json"):
        shutil.copy(NETWORKS_DIR / n, OUT / n)

    dump("terms.json", {
        "top_terms": records(pd.read_csv(T / "term_frequencies.csv").head(60)),
        "tfidf_by_chapter": records(pd.read_csv(T / "tfidf_by_chapter.csv")),
        "bigrams": records(pd.read_csv(T / "bigrams.csv").head(40)),
        "trigrams": records(pd.read_csv(T / "trigrams.csv").head(30)),
    })
    dump("topics.json", {
        "summary": records(pd.read_csv(T / "topics_summary.csv")),
        "examples": records(pd.read_csv(T / "topic_examples.csv")),
        "by_chapter": records(pd.read_csv(T / "topics_by_chapter.csv")),
        "agreement": records(pd.read_csv(T / "topic_model_agreement.csv")),
        "k_sweep": records(pd.read_csv(T / "topic_k_sweep.csv")),
    })
    emap = pd.read_csv(T / "embedding_map.csv")
    dump("embedding_map.json", records(emap))
    dump("framing.json", {
        "by_chapter": records(pd.read_csv(T / "framing_by_chapter.csv")),
        "sentiment_by_chapter": records(pd.read_csv(T / "sentiment_by_chapter.csv")),
        "causal_sentences": records(pd.read_csv(T / "causal_sentences.csv")),
    })
    feats = pd.read_csv(T / "stylometry_features.csv")
    fcols = ["segment_id", "avg_sentence_length", "sentence_length_cv", "avg_word_length", "mattr_100", "hapax_ratio",
             "lexical_density", "fernandez_huerta", "connectors_per_1k", "hedging_per_1k", "certainty_per_1k",
             "numbers_per_1k", "pattern_no_x_sino_y_per_1k", "pattern_triad_list_per_1k",
             "pattern_headline_colon_per_1k", "pattern_stock_phrases_per_1k", "pattern_em_dash_per_1k"]
    dump("stylometry.json", {
        "segments": records(pd.read_csv(T / "stylometry_segment_scores.csv").merge(feats[fcols], on="segment_id")),
        "change_points": records(pd.read_csv(T / "stylometry_change_points.csv")),
        "sensitivity": records(pd.read_csv(T / "stylometry_change_point_sensitivity.csv")),
        "clustering": records(pd.read_csv(T / "stylometry_clustering.csv")),
        "pca_variance": records(pd.read_csv(T / "stylometry_pca_variance.csv")),
        "provenance_statements": records(pd.read_csv(T / "provenance_statements.csv")),
    })
    dump("methodology.json", {"markdown": (DOCUMENTS_DIR / "methodology.md").read_text(encoding="utf-8"),
                              "limitations": (DOCUMENTS_DIR / "limitations.md").read_text(encoding="utf-8")
                              if (DOCUMENTS_DIR / "limitations.md").exists() else ""})


if __name__ == "__main__":
    main()
