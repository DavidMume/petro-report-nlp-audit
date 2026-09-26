"""Claim extraction: builds data/processed/claims.csv per CLAIMS_SCHEMA.

Automated extraction is a first pass only — documents/methodology.md is
explicit that no automatically extracted sentence is treated as a
definitive claim without human review before it enters the claims table
used for verification.
"""

from __future__ import annotations

import pandas as pd

from src.config import CLAIM_TYPES, CLAIMS_SCHEMA

# Cue terms that raise a sentence's priority for claim-candidate review —
# NOT a filter that silently excludes everything else.
CLAIM_CUE_PATTERNS_ES = [
    r"\d+([.,]\d+)?\s*%",  # percentages
    r"\b(19|20)\d{2}\b",  # years
    r"\b(millones|billones|mil millones)\b",
    r"\b(aumentó|disminuyó|creció|cayó|se redujo|se incrementó)\b",
    r"\b(según|de acuerdo con|reportó|indicó)\b",  # attribution
]


def build_empty_claims_table() -> pd.DataFrame:
    """Return an empty DataFrame with the canonical claims schema."""
    return pd.DataFrame(columns=CLAIMS_SCHEMA)


def extract_candidate_claims(corpus_df: pd.DataFrame) -> pd.DataFrame:
    """First-pass, rule-assisted extraction of claim CANDIDATES (numbers,
    percentages, dates, comparative/causal language, institutional
    statements). Output is provisional and requires human review — see
    documents/methodology.md §12.

    TODO: implement once the corpus exists.
    """
    raise NotImplementedError("Candidate claim extraction not yet implemented.")


def classify_claim_type(claim_text: str) -> str:
    """Suggest a claim_type from CLAIM_TYPES for human confirmation — this
    is a suggestion, not an authoritative label.

    TODO: implement (rule-based or classifier).
    """
    raise NotImplementedError("Claim type classification not yet implemented.")
