"""Provenance and traceability checks on the committed data (skipped if absent)."""

import json

import pandas as pd
import pytest

from src.config import CLAIMS_PATH, CORPUS_CSV_PATH, RAW_DIR, SOURCE_METADATA_PATH
from src.extract import compute_sha256


def test_raw_pdf_hash_matches_metadata():
    meta = json.loads(SOURCE_METADATA_PATH.read_text(encoding="utf-8"))
    if not meta.get("filename") or not (RAW_DIR / meta["filename"]).exists():
        pytest.skip("source PDF not present")
    assert compute_sha256(RAW_DIR / meta["filename"]) == meta["sha256"]
    fields = {k: v for k, v in meta.items() if k != "notes"}
    assert "ADLA" not in json.dumps(fields)  # unverified acronym must not be adopted as title/publisher/author


def test_every_sentence_traces_to_a_page():
    df = pd.read_csv(CORPUS_CSV_PATH)
    if df.empty:
        pytest.skip("corpus not built")
    meta = json.loads(SOURCE_METADATA_PATH.read_text(encoding="utf-8"))
    assert df.page.between(1, meta["pages"]).all()
    assert df.sentence_id.is_unique
    assert df[["document_id", "page", "section", "paragraph_id", "sentence_id"]].notna().all().all()


def test_claims_point_to_real_sentences_on_the_same_page():
    claims, corpus = pd.read_csv(CLAIMS_PATH), pd.read_csv(CORPUS_CSV_PATH)
    if claims.empty or corpus.empty:
        pytest.skip("claims not extracted")
    m = claims.merge(corpus[["sentence_id", "page", "clean_text"]], on="sentence_id", suffixes=("", "_corpus"))
    assert len(m) == len(claims)
    assert (m.page == m.page_corpus).all()
    assert (m.claim_text == m.clean_text).all()
