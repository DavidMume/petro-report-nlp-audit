#!/usr/bin/env python3
"""Validate the curated verification records and build merged views.

Inputs (curated, version-controlled):
  data/processed/claim_evidence.csv, data/processed/claim_assessments.csv,
  sources/evidence_ledger.csv, sources/numeric_reconstructions.csv
Inputs (generated): data/processed/claims.csv, data/processed/numeric_claims.csv

Outputs:
  outputs/tables/claims_with_assessments.csv
  outputs/tables/verification_coverage.csv
  data/processed/numeric_claims.csv  (auto rows + curated reconstruction rows)

Fails loudly if any assessment lacks explicit external evidence, cites a
source missing from the ledger, relies on circular coverage of the report,
or has drifted from the sentence it was made about.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (CLAIM_ASSESSMENTS_PATH, CLAIM_EVIDENCE_PATH, CLAIMS_PATH, EVIDENCE_LEDGER_PATH,
                        NUMERIC_CLAIMS_PATH, SOURCES_DIR, TABLES_DIR)
from src.validation import assert_valid, coverage_summary, merged_claims_view


def main() -> None:
    if not CLAIMS_PATH.exists():
        raise FileNotFoundError(f"{CLAIMS_PATH} not found — run `make claims` first.")
    claims = pd.read_csv(CLAIMS_PATH)
    evidence = pd.read_csv(CLAIM_EVIDENCE_PATH)
    assessments = pd.read_csv(CLAIM_ASSESSMENTS_PATH).fillna({"robustness": "", "context_flags": ""})
    ledger = pd.read_csv(EVIDENCE_LEDGER_PATH)
    assert_valid(claims, evidence, assessments, ledger)

    merged = merged_claims_view(claims, assessments)
    merged.to_csv(TABLES_DIR / "claims_with_assessments.csv", index=False)
    cov = coverage_summary(claims, assessments)
    cov.to_csv(TABLES_DIR / "verification_coverage.csv", index=False)

    recon_path = SOURCES_DIR / "numeric_reconstructions.csv"
    if recon_path.exists():
        auto = pd.read_csv(NUMERIC_CLAIMS_PATH)
        auto = auto[~auto.notes.fillna("").str.startswith("RECONSTRUCTED")]
        recon = pd.read_csv(recon_path)
        recon["notes"] = "RECONSTRUCTED (curated): " + recon.notes.fillna("")
        pd.concat([recon, auto], ignore_index=True).to_csv(NUMERIC_CLAIMS_PATH, index=False)

    print(f"[validate] OK: {len(assessments)} assessments, {len(evidence)} evidence rows, "
          f"{len(ledger)} ledger sources")
    print(cov.to_string(index=False))


if __name__ == "__main__":
    main()
