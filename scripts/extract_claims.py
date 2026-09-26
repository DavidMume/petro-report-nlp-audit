#!/usr/bin/env python3
"""Run first-pass, rule-assisted claim-candidate extraction over the corpus
and write data/processed/claims.csv (still subject to human review before
any claim is treated as definitive — see documents/methodology.md §12).

Usage:
    python scripts/extract_claims.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.claims import build_empty_claims_table, extract_candidate_claims
from src.config import CLAIMS_PATH
from src.corpus import load_corpus


def main() -> None:
    corpus_df = load_corpus()
    # TODO: replace with a real call once src/claims.py is implemented.
    candidates = extract_candidate_claims(corpus_df)  # currently raises NotImplementedError
    candidates.to_csv(CLAIMS_PATH, index=False)
    print(f"[extract_claims] Wrote {len(candidates)} candidate claims to {CLAIMS_PATH}")


if __name__ == "__main__":
    main()
