"""The verification contract: no assessment without explicit external evidence."""

import pandas as pd
import pytest

from src.config import CLAIM_ASSESSMENTS_PATH, CLAIM_EVIDENCE_PATH, CLAIMS_PATH, EVIDENCE_LEDGER_PATH
from src.validation import check_integrity

CLAIMS = pd.DataFrame({"claim_id": ["C1", "C2"], "sentence_id": ["P1-S01", "P2-S01"],
                       "claim_text": ["La DIAN recaudó X.", "Opinión sobre el país."]})
LEDGER = pd.DataFrame({"source_id": ["S1", "S0", "SX"],
                       "source_type": ["official_statistical_publication", "audited_document",
                                       "coverage_of_audited_document"]})


def ev(cid, sid, stype, supports=True):
    return {"claim_id": cid, "source_id": sid, "source_name": "n", "source_url": "u", "source_type": stype,
            "publication_date": "", "access_date": "2026-09-28", "evidence_excerpt": "e", "supports": supports,
            "contradicts": False, "contextualises": False, "reliability_notes": ""}


def asmt(cid, status, sent="P1-S01", prefix="La DIAN"):
    return {"claim_id": cid, "assessment": status, "confidence": "high", "reasoning_summary": "r",
            "sentence_id": sent, "claim_text_prefix": prefix, "robustness": ""}


def test_valid_records_pass():
    E = pd.DataFrame([ev("C1", "S1", "official_statistical_publication"), ev("C2", "S0", "audited_document")])
    A = pd.DataFrame([asmt("C1", "supported"),
                      asmt("C2", "opinion_or_interpretation", "P2-S01", "Opinión")])
    assert check_integrity(CLAIMS, E, A, LEDGER) == []


def test_factual_status_needs_external_evidence():
    E = pd.DataFrame([ev("C1", "S0", "audited_document")])
    A = pd.DataFrame([asmt("C1", "supported")])
    assert any("without external evidence" in p for p in check_integrity(CLAIMS, E, A, LEDGER))


def test_invalid_status_missing_evidence_and_circular_sources_are_rejected():
    E = pd.DataFrame([ev("C1", "SX", "reputable_journalism")])
    A = pd.DataFrame([asmt("C1", "true"), asmt("C2", "supported", "P2-S01", "Opinión")])
    problems = check_integrity(CLAIMS, E, A, LEDGER)
    assert any("invalid assessment" in p for p in problems)
    assert any("C2: no evidence rows" in p for p in problems)
    assert any("circular" in p for p in problems)


def test_drifted_claim_ids_are_detected():
    E = pd.DataFrame([ev("C1", "S1", "official_statistical_publication")])
    A = pd.DataFrame([asmt("C1", "supported", sent="P9-S09")])
    assert any("drifted" in p for p in check_integrity(CLAIMS, E, A, LEDGER))


def test_repository_verification_files_are_valid():
    if not CLAIMS_PATH.exists() or not CLAIM_ASSESSMENTS_PATH.exists():
        pytest.skip("pipeline outputs not present")
    claims = pd.read_csv(CLAIMS_PATH)
    if claims.empty:
        pytest.skip("no claims extracted yet")
    problems = check_integrity(claims, pd.read_csv(CLAIM_EVIDENCE_PATH),
                               pd.read_csv(CLAIM_ASSESSMENTS_PATH).fillna({"robustness": ""}),
                               pd.read_csv(EVIDENCE_LEDGER_PATH))
    assert problems == []
