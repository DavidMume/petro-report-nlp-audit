#!/usr/bin/env python3
"""Exploratory linguistic-provenance analysis (RQ6/RQ7).

Writes:
  data/processed/stylometry_segments.csv          segments (segment_id, pages, section, word_count, raw_text, …)
  outputs/tables/stylometry_features.csv          per-segment features
  outputs/tables/stylometry_segment_scores.csv    Mahalanobis / JS / cluster per segment
  outputs/tables/stylometry_change_points.csv     change points along the document
  outputs/tables/stylometry_clustering.csv        silhouette + ARI vs chapters
  outputs/tables/stylometry_similarity_cosine.csv, stylometry_js_divergence.csv
  outputs/tables/stylometry_pca_{variance,loadings}.csv
  outputs/tables/ai_detector_status.json          detectors: not run (reason)
  outputs/tables/provenance_statements.csv        what the document itself says about AI use
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import authorship as au
from src.config import STYLOMETRY_SEGMENTS_PATH, TABLES_DIR
from src.corpus import analytic, load_corpus, load_paragraphs


def main() -> None:
    corpus = analytic(load_corpus())
    paragraphs = load_paragraphs()
    segs = au.segment_document(corpus)
    segs.to_csv(STYLOMETRY_SEGMENTS_PATH, index=False)
    feats = au.compute_stylometric_features(segs, paragraphs)
    feats.to_csv(TABLES_DIR / "stylometry_features.csv", index=False)
    res = au.analyse_internal_consistency(feats, segs)
    res["segment_scores"].to_csv(TABLES_DIR / "stylometry_segment_scores.csv", index=False)
    res["change_points"].to_csv(TABLES_DIR / "stylometry_change_points.csv", index=False)
    res["clustering"].to_csv(TABLES_DIR / "stylometry_clustering.csv", index=False)
    res["change_point_sensitivity"].to_csv(TABLES_DIR / "stylometry_change_point_sensitivity.csv", index=False)
    res["cosine"].to_csv(TABLES_DIR / "stylometry_similarity_cosine.csv")
    res["js_divergence"].to_csv(TABLES_DIR / "stylometry_js_divergence.csv")
    res["pca_variance"].to_csv(TABLES_DIR / "stylometry_pca_variance.csv", index=False)
    res["pca_loadings"].to_csv(TABLES_DIR / "stylometry_pca_loadings.csv", index=False)
    # Detector results come from scripts/analyse_detector_calibration.py once it has run.
    if not (TABLES_DIR / "detector_calibration_status.json").exists():
        (TABLES_DIR / "ai_detector_status.json").write_text(
            json.dumps(au.DETECTOR_STATUS, indent=2, ensure_ascii=False) + "\n")

    # What the document itself states about AI use (author acknowledgement, §33).
    p = paragraphs
    mask = p.clean_text.str.contains(r"inteligencia artificial", case=False)
    prov = p[mask][["paragraph_id", "page", "section", "clean_text"]].copy()
    prov["evidence_type"] = "author_acknowledgement_in_document"
    prov["scope_note"] = ("States AI tools supported document organisation, analytic consolidation, prioritisation, "
                          "traceability, information processing and 'organización de los insumos de los productos "
                          "finales'; does not state whether AI tools drafted any text.")
    prov.to_csv(TABLES_DIR / "provenance_statements.csv", index=False)

    sc = res["segment_scores"]
    print(f"[authorship] segments={len(segs)} (short={int(segs.short_segment.sum())}); "
          f"features={feats.shape[1] - 1}; outliers={int(sc.flag_stylistic_outlier.sum())}; "
          f"change_points={len(res['change_points'])}")
    print(res["clustering"].to_string(index=False))
    print(res["change_points"].to_string(index=False))
    print(sc[sc.flag_stylistic_outlier][["segment_id", "pages", "chapter", "section", "mahalanobis_sq"]].to_string(index=False))


if __name__ == "__main__":
    main()
