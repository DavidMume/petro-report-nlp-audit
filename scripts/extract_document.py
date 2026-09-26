#!/usr/bin/env python3
"""Extract the source PDF from data/raw/ into page-level text, and populate
documents/source_metadata.json's filename/sha256/pages fields.

Usage:
    python scripts/extract_document.py [--pdf PATH]

If --pdf is omitted, the script looks for exactly one PDF in data/raw/.
Refuses to run if no PDF is present (per the project's rule against
inventing or assuming a source document — see documents/methodology.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import RAW_DIR, SOURCE_METADATA_PATH
from src.extract import compute_sha256, extract_document


def find_source_pdf(explicit_path: str | None) -> Path:
    if explicit_path:
        pdf_path = Path(explicit_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"No such file: {pdf_path}")
        return pdf_path

    candidates = sorted(RAW_DIR.glob("*.pdf"))
    if not candidates:
        raise FileNotFoundError(
            f"No PDF found in {RAW_DIR}. Place the confirmed source document "
            "there first (see data/raw/README.md) — this pipeline does not "
            "invent or assume a source document."
        )
    if len(candidates) > 1:
        raise RuntimeError(
            f"Multiple PDFs found in {RAW_DIR}: {[p.name for p in candidates]}. "
            "Pass --pdf explicitly to disambiguate."
        )
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", default=None, help="Explicit path to the source PDF")
    args = parser.parse_args()

    pdf_path = find_source_pdf(args.pdf)
    print(f"[extract_document] Source: {pdf_path}")

    sha256 = compute_sha256(pdf_path)
    print(f"[extract_document] SHA-256: {sha256}")

    # Update the filename/sha256 fields in source_metadata.json without
    # clobbering any manually-filled fields (title, publisher, etc.).
    metadata = json.loads(SOURCE_METADATA_PATH.read_text(encoding="utf-8"))
    metadata["filename"] = pdf_path.name
    metadata["sha256"] = sha256
    SOURCE_METADATA_PATH.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[extract_document] Updated {SOURCE_METADATA_PATH}")

    # Full page extraction (raises NotImplementedError at the scaffolding
    # stage — src/extract.py is filled in once the document is confirmed).
    extract_document(pdf_path)


if __name__ == "__main__":
    main()
