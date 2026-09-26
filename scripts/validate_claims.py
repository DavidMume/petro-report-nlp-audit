#!/usr/bin/env python3
"""Run claim verification against the evidence ledger, producing
data/processed/claim_evidence.csv and data/processed/claim_assessments.csv.

Refuses to auto-classify from LLM judgement alone — every assessment must
cite an explicit evidence row (see documents/methodology.md §13 and
src/validation.py).

Usage:
    python scripts/validate_claims.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CLAIM_ASSESSMENTS_PATH, CLAIM_EVIDENCE_PATH, CLAIMS_PATH


def main() -> None:
    if not CLAIMS_PATH.exists():
        raise FileNotFoundError(
            f"{CLAIMS_PATH} not found. Run scripts/extract_claims.py (and "
            "complete human review of the resulting candidates) first."
        )
    # TODO: for each reviewed claim, gather evidence rows (manually curated
    # or scripted retrieval against named sources — see src/sources.py) and
    # call src.validation.assess_claim(). Left unimplemented at the
    # scaffolding stage.
    raise NotImplementedError(
        "validate_claims.py is scaffolded but the verification logic in "
        "src/validation.py is not yet implemented — see RESEARCH_LOG.md."
    )


if __name__ == "__main__":
    main()
