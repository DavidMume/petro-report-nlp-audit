#!/usr/bin/env python3
"""First-pass, rule-assisted claim-candidate extraction.

Writes:
  data/processed/claims.csv          all candidates (factual + evaluative), review_status=auto_candidate
  data/processed/numeric_claims.csv  quantities from factual candidates (reconstruction columns empty)
  outputs/tables/causal_claims_review.csv  causal-language claim candidates for special review

Usage:
    python scripts/extract_claims.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.claims import CLAIMS_EXTRA_COLUMNS, extract_candidate_claims, numeric_claims_table
from src.config import CLAIMS_PATH, CLAIMS_SCHEMA, NUMERIC_CLAIMS_PATH, TABLES_DIR
from src.corpus import analytic, load_corpus


def main() -> None:
    corpus = analytic(load_corpus())
    claims = extract_candidate_claims(corpus)
    numeric = numeric_claims_table(claims, corpus)
    claims[CLAIMS_SCHEMA + CLAIMS_EXTRA_COLUMNS].to_csv(CLAIMS_PATH, index=False)
    numeric.to_csv(NUMERIC_CLAIMS_PATH, index=False)
    causal = claims[claims.is_causal][["claim_id", "page", "section", "claim_type", "claim_text",
                                        "cues", "source_cited_in_report"]].copy()
    causal["causal_review_question"] = ("Does the report show evidence for the causal link, or only a temporal "
                                        "co-occurrence? (see methodology §14)")
    causal["review_status"] = "pending_human_review"
    causal.to_csv(TABLES_DIR / "causal_claims_review.csv", index=False)
    print(f"[claims] candidates={len(claims)} "
          f"(factual={int((claims.claim_kind == 'factual_candidate').sum())}, "
          f"evaluative={int((claims.claim_kind == 'evaluative_candidate').sum())}); "
          f"numeric={len(numeric)}; causal={len(causal)}")
    print(claims.groupby(["priority"]).size().to_string())
    print(claims.claim_type.value_counts().to_string())


if __name__ == "__main__":
    main()
