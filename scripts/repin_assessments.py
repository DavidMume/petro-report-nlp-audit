#!/usr/bin/env python3
"""Re-attach curated verification records to claims after claim IDs shift.

Claim IDs are sequential, so a change in extraction (e.g. a repaired block
that merges two paragraphs) can renumber them. Assessments store the
claim's text prefix; this script finds each prefix in the new claims.csv and
rewrites claim_id / sentence_id in every curated file. It refuses to guess:
a prefix that matches zero or several claims stops the script.

Usage:
    python scripts/repin_assessments.py            # dry run
    python scripts/repin_assessments.py --write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CLAIM_ASSESSMENTS_PATH, CLAIM_EVIDENCE_PATH, CLAIMS_PATH, EVIDENCE_LEDGER_PATH, SOURCES_DIR, TABLES_DIR


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    claims = pd.read_csv(CLAIMS_PATH)
    assess = pd.read_csv(CLAIM_ASSESSMENTS_PATH)
    mapping = {}
    for _, a in assess.iterrows():
        hits = claims[claims.claim_text.str.startswith(str(a.claim_text_prefix))]
        if len(hits) != 1:
            raise SystemExit(f"{a.claim_id}: prefix matches {len(hits)} claims — resolve manually")
        h = hits.iloc[0]
        mapping[a.claim_id] = (h.claim_id, h.sentence_id)
    changed = {k: v for k, v in mapping.items() if k != v[0]}
    for old, (new, sid) in mapping.items():
        print(f"{old} -> {new} ({sid})" + ("" if old == new else "  *changed*"))
    if not args.write or not changed:
        return
    idmap = {k: v[0] for k, v in mapping.items()}
    assess["sentence_id"] = assess.claim_id.map(lambda x: mapping[x][1])
    assess["claim_id"] = assess.claim_id.map(idmap)
    assess.to_csv(CLAIM_ASSESSMENTS_PATH, index=False)
    ev = pd.read_csv(CLAIM_EVIDENCE_PATH)
    ev["claim_id"] = ev.claim_id.map(lambda x: idmap.get(x, x))
    ev.to_csv(CLAIM_EVIDENCE_PATH, index=False)
    led = pd.read_csv(EVIDENCE_LEDGER_PATH)
    led["claim_ids"] = led.claim_ids.fillna("").map(lambda s: ";".join(idmap.get(x, x) for x in s.split(";") if x))
    led.to_csv(EVIDENCE_LEDGER_PATH, index=False)
    for path in (SOURCES_DIR / "numeric_reconstructions.csv", TABLES_DIR / "source_triangulation.csv"):
        df = pd.read_csv(path)
        df["claim_id"] = df.claim_id.map(lambda x: idmap.get(x, x))
        df.to_csv(path, index=False)
    print(f"[repin] rewrote {len(changed)} claim IDs across curated files")


if __name__ == "__main__":
    main()
