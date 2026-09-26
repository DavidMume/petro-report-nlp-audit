"""Minimal tests for src/claims.py and the claims schema."""

import pytest

from src.claims import build_empty_claims_table, extract_candidate_claims
from src.config import CLAIM_TYPES, CLAIMS_SCHEMA, VERIFICATION_STATUSES


def test_claims_schema_matches_spec():
    expected = [
        "claim_id", "claim_text", "short_quote", "page", "section",
        "claim_type", "subject", "predicate", "object", "time_period",
        "numeric_value", "unit", "source_cited_in_report", "verifiable",
        "verification_status", "confidence", "notes",
    ]
    assert CLAIMS_SCHEMA == expected


def test_build_empty_claims_table_has_correct_columns():
    df = build_empty_claims_table()
    assert list(df.columns) == CLAIMS_SCHEMA
    assert len(df) == 0


def test_claim_types_cover_spec_categories():
    expected_subset = {
        "economico", "fiscal", "empleo", "seguridad", "salud", "energia",
        "instituciones", "corrupcion", "politica_social", "infraestructura",
        "relaciones_internacionales", "otros",
    }
    assert expected_subset.issubset(set(CLAIM_TYPES))


def test_verification_statuses_are_non_binary():
    """Guards against collapsing the assessment categories back down to a
    simple true/false, which the project's methodology explicitly rejects.
    """
    assert "true" not in VERIFICATION_STATUSES
    assert "false" not in VERIFICATION_STATUSES
    assert len(VERIFICATION_STATUSES) == 8


def test_extract_candidate_claims_not_yet_implemented():
    with pytest.raises(NotImplementedError):
        extract_candidate_claims(None)
