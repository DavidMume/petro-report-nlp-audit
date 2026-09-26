"""Sanity checks on paths and schema constants in src/config.py — cheap
tests that catch typos/renames early without needing any real data."""

from src.config import (
    CLAIM_ASSESSMENTS_SCHEMA,
    CLAIM_EVIDENCE_SCHEMA,
    CORPUS_SCHEMA,
    EVIDENCE_LEDGER_SCHEMA,
    NUMERIC_CLAIMS_SCHEMA,
    ROOT_DIR,
    SOURCE_PRIORITY,
)


def test_root_dir_exists():
    assert ROOT_DIR.exists()
    assert (ROOT_DIR / "src").exists()
    assert (ROOT_DIR / "data").exists()


def test_corpus_schema_has_traceability_fields():
    for field in ["document_id", "page", "section", "paragraph_id", "sentence_id"]:
        assert field in CORPUS_SCHEMA


def test_claim_evidence_schema_requires_access_date():
    assert "access_date" in CLAIM_EVIDENCE_SCHEMA
    assert "publication_date" in CLAIM_EVIDENCE_SCHEMA


def test_claim_assessments_schema_requires_reasoning():
    assert "reasoning_summary" in CLAIM_ASSESSMENTS_SCHEMA


def test_numeric_claims_schema_supports_reconstruction():
    for field in ["reported_value", "reconstructed_value", "difference_percent", "method"]:
        assert field in NUMERIC_CLAIMS_SCHEMA


def test_evidence_ledger_schema_has_provenance_fields():
    for field in ["sha256", "access_date", "primary_or_secondary"]:
        assert field in EVIDENCE_LEDGER_SCHEMA


def test_source_priority_ranks_official_data_first():
    assert SOURCE_PRIORITY[0] == "raw_official_dataset"
    assert "social_media" in SOURCE_PRIORITY
    assert SOURCE_PRIORITY.index("social_media") == len(SOURCE_PRIORITY) - 1
