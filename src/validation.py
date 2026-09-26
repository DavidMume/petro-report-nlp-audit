"""Claim verification against external evidence.

Implements the schemas for data/processed/claim_evidence.csv and
data/processed/claim_assessments.csv. Per documents/methodology.md, no
verification_status is ever assigned from LLM judgement alone — every
assessment must cite explicit external evidence rows in claim_evidence.csv.
"""

from __future__ import annotations

import pandas as pd

from src.config import (
    CLAIM_ASSESSMENTS_SCHEMA,
    CLAIM_EVIDENCE_SCHEMA,
    NUMERIC_CLAIMS_SCHEMA,
    VERIFICATION_STATUSES,
)


def build_empty_evidence_table() -> pd.DataFrame:
    return pd.DataFrame(columns=CLAIM_EVIDENCE_SCHEMA)


def build_empty_assessments_table() -> pd.DataFrame:
    return pd.DataFrame(columns=CLAIM_ASSESSMENTS_SCHEMA)


def build_empty_numeric_claims_table() -> pd.DataFrame:
    return pd.DataFrame(columns=NUMERIC_CLAIMS_SCHEMA)


def assess_claim(claim_id: str, evidence_rows: pd.DataFrame) -> dict:
    """Given all evidence rows collected for a claim_id, propose an
    assessment. Must require at least one evidence row with a non-null
    source_url/source_name before returning any status other than
    'not_independently_verifiable'.

    TODO: implement once real claims + evidence exist. This function
    produces a *proposed* assessment for human confirmation, consistent
    with documents/methodology.md's ban on LLM-only classification.
    """
    raise NotImplementedError("Claim assessment not yet implemented.")


def reconstruct_numeric_claim(claim_id: str, independent_dataset) -> dict:
    """Attempt to reconstruct a reported numeric claim from an independent
    dataset (see documents/methodology.md §24 "Cross-data validation" for
    the reconstruction principle: identify period, population, definition,
    then recompute).

    TODO: implement per-claim once specific numeric claims and matching
    datasets have been identified.
    """
    raise NotImplementedError("Numeric claim reconstruction not yet implemented.")


assert set(VERIFICATION_STATUSES) == {
    "supported",
    "mostly_supported",
    "mixed_or_disputed",
    "misleading_without_context",
    "unsupported",
    "contradicted",
    "not_independently_verifiable",
    "opinion_or_interpretation",
}
