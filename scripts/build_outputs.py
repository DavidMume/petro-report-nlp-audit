#!/usr/bin/env python3
"""Regenerate all charts (outputs/charts/), network exports
(outputs/networks/), and the data provenance manifest
(outputs/data_manifest.json) from the processed data tables.

Usage:
    python scripts/build_outputs.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_MANIFEST_PATH, PROCESSED_DIR
from src.visualisations import CHART_REGISTRY


def build_data_manifest() -> dict:
    """Record filename, source, download_date, sha256, rows, columns, and
    processing_script for each dataset in data/processed/ — see
    documents/methodology.md §29.

    TODO: implement fully once processed datasets exist; currently returns
    an empty, correctly-shaped manifest so downstream tooling has something
    valid to read.
    """
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "datasets": [],
    }


def main() -> None:
    manifest = build_data_manifest()
    DATA_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[build_outputs] Wrote {DATA_MANIFEST_PATH} (empty — no processed datasets yet)")

    print(f"[build_outputs] {len(CHART_REGISTRY)} charts registered in src/visualisations.py; "
          "none generated yet (plotting functions are not yet implemented).")


if __name__ == "__main__":
    main()
