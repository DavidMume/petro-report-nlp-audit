"""Claim verification: schema, integrity checks and merged views.

Assessments are NOT produced by code. They are curated records
(data/processed/claim_assessments.csv) that must each cite explicit
external evidence rows (data/processed/claim_evidence.csv) registered in
sources/evidence_ledger.csv. This module enforces that contract:

- every assessment uses one of the eight VERIFICATION_STATUSES;
- every assessment has >= 1 evidence row, and every factual status
  (anything except opinion_or_interpretation / not_independently_verifiable)
  has >= 1 evidence row from a source other than the audited document itself;
- every evidence source_id exists in the evidence ledger, with an access date;
- evidence from `coverage_of_audited_document` sources (media reproducing the
  report) is rejected as circular;
- each assessment is pinned to the claim's sentence_id and text prefix, so
  a re-run of claim extraction that shifts claim IDs is detected instead of
  silently re-attaching assessments to different sentences.
"""

from __future__ import annotations

import pandas as pd

from src.config import (
    CLAIM_ASSESSMENTS_SCHEMA,
    CLAIM_EVIDENCE_SCHEMA,
    NUMERIC_CLAIMS_SCHEMA,
    VERIFICATION_STATUSES,
)

NON_FACTUAL_STATUSES = {"opinion_or_interpretation", "not_independently_verifiable"}
ROBUSTNESS_LABELS = {"robust", "moderately robust", "sensitive to assumptions", "insufficient evidence", ""}


class ValidationError(ValueError):
    pass


def build_empty_evidence_table() -> pd.DataFrame:
    return pd.DataFrame(columns=CLAIM_EVIDENCE_SCHEMA)


def build_empty_assessments_table() -> pd.DataFrame:
    return pd.DataFrame(columns=CLAIM_ASSESSMENTS_SCHEMA)


def build_empty_numeric_claims_table() -> pd.DataFrame:
    return pd.DataFrame(columns=NUMERIC_CLAIMS_SCHEMA)


def check_integrity(claims: pd.DataFrame, evidence: pd.DataFrame, assessments: pd.DataFrame,
                    ledger: pd.DataFrame) -> list[str]:
    """Return a list of problems (empty list = valid)."""
    problems = []
    claims_idx = claims.set_index("claim_id")
    ledger_idx = ledger.set_index("source_id")
    for col in CLAIM_ASSESSMENTS_SCHEMA:
        if col not in assessments.columns:
            problems.append(f"claim_assessments.csv missing column {col}")
    for col in CLAIM_EVIDENCE_SCHEMA:
        if col not in evidence.columns:
            problems.append(f"claim_evidence.csv missing column {col}")
    if problems:
        return problems

    for _, a in assessments.iterrows():
        cid = a.claim_id
        if a.assessment not in VERIFICATION_STATUSES:
            problems.append(f"{cid}: invalid assessment '{a.assessment}'")
        if cid not in claims_idx.index:
            problems.append(f"{cid}: not in claims.csv")
            continue
        c = claims_idx.loc[cid]
        if "sentence_id" in a and pd.notna(a.get("sentence_id")) and a.sentence_id != c.sentence_id:
            problems.append(f"{cid}: pinned sentence {a.sentence_id} != claims.csv sentence {c.sentence_id} (IDs drifted)")
        if "claim_text_prefix" in a and pd.notna(a.get("claim_text_prefix")) \
                and not str(c.claim_text).startswith(str(a.claim_text_prefix)):
            problems.append(f"{cid}: claim text changed since assessment")
        ev = evidence[evidence.claim_id == cid]
        if ev.empty:
            problems.append(f"{cid}: no evidence rows")
            continue
        if a.assessment not in NON_FACTUAL_STATUSES:
            external = ev[ev.source_type != "audited_document"]
            if external.empty:
                problems.append(f"{cid}: factual assessment without external evidence")
        if "robustness" in a and str(a.get("robustness") if pd.notna(a.get("robustness")) else "") not in ROBUSTNESS_LABELS:
            problems.append(f"{cid}: invalid robustness label {a.robustness}")

    for _, e in evidence.iterrows():
        if e.source_id not in ledger_idx.index:
            problems.append(f"evidence {e.claim_id}/{e.source_id}: source not in evidence ledger")
            continue
        led = ledger_idx.loc[e.source_id]
        if led.source_type == "coverage_of_audited_document":
            problems.append(f"evidence {e.claim_id}/{e.source_id}: circular source (coverage of the audited report)")
        if not isinstance(e.access_date, str) or not e.access_date:
            problems.append(f"evidence {e.claim_id}/{e.source_id}: missing access_date")
        if not (bool(e.supports) or bool(e.contradicts) or bool(e.contextualises)):
            problems.append(f"evidence {e.claim_id}/{e.source_id}: supports/contradicts/contextualises all false")
    return problems


def assert_valid(*args) -> None:
    problems = check_integrity(*args)
    if problems:
        raise ValidationError("Verification data failed integrity checks:\n  - " + "\n  - ".join(problems))


def merged_claims_view(claims: pd.DataFrame, assessments: pd.DataFrame) -> pd.DataFrame:
    """claims.csv with the curated assessment (if any) joined in; unassessed
    claims keep verification_status='unassessed'."""
    cols = ["claim_id", "assessment", "confidence", "reasoning_summary", "robustness", "context_flags",
            "components_checked", "components_unverified", "evidence_source_ids"]
    m = claims.drop(columns=["confidence"], errors="ignore").merge(
        assessments[[c for c in cols if c in assessments.columns]], on="claim_id", how="left")
    m["verification_status"] = m.assessment.fillna("unassessed")
    return m.drop(columns=["assessment"])


def coverage_summary(claims: pd.DataFrame, assessments: pd.DataFrame) -> pd.DataFrame:
    """RQ4 bookkeeping: how many candidates exist, how many were assessed."""
    factual = claims[claims.claim_kind == "factual_candidate"]
    rows = [
        {"metric": "claim_candidates_total", "value": len(claims)},
        {"metric": "factual_candidates", "value": len(factual)},
        {"metric": "evaluative_candidates", "value": int((claims.claim_kind == "evaluative_candidate").sum())},
        {"metric": "factual_candidates_verifiable_yes_candidate", "value": int((factual.verifiable == "yes_candidate").sum())},
        {"metric": "assessed_total", "value": len(assessments)},
        {"metric": "assessed_share_of_factual_candidates_pct",
         "value": round(100 * len(assessments[~assessments.assessment.isin(NON_FACTUAL_STATUSES)]) / max(len(factual), 1), 2)},
    ]
    for s in VERIFICATION_STATUSES:
        rows.append({"metric": f"assessed_{s}", "value": int((assessments.assessment == s).sum())})
    return pd.DataFrame(rows)


def assess_claim(claim_id: str, evidence_rows: pd.DataFrame) -> dict:
    """Deliberately not automated (see module docstring)."""
    raise NotImplementedError(
        "Assessments are curated with explicit external evidence and recorded in "
        "data/processed/claim_assessments.csv; they are not generated automatically."
    )


def reconstruct_numeric_claim(reported: float, reconstructed: float) -> dict:
    """Difference between a reported value and one reconstructed from an
    independent dataset (same unit and period assumed — check before use)."""
    diff = reconstructed - reported
    return {"difference_absolute": round(diff, 6),
            "difference_percent": round(100 * diff / reported, 4) if reported else None}


assert set(VERIFICATION_STATUSES) == {
    "supported", "mostly_supported", "mixed_or_disputed", "misleading_without_context", "unsupported",
    "contradicted", "not_independently_verifiable", "opinion_or_interpretation",
}
