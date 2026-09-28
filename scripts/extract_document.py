#!/usr/bin/env python3
"""Extract the source PDF from data/raw/ into block-level page records
(data/interim/pages.jsonl), tables (data/interim/tables/), and an extraction
log (outputs/tables/extraction_log.csv). Verifies the file hash against
documents/source_metadata.json and refuses to run on a mismatch, so a silently
replaced source file can never be analysed.

Usage:
    python scripts/extract_document.py [--pdf PATH] [--no-ocr]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import INTERIM_DIR, RAW_DIR, SOURCE_METADATA_PATH, TABLES_DIR
from src.extract import compute_sha256, extract_document, save_pages


def find_source_pdf(explicit_path: str | None) -> Path:
    if explicit_path:
        pdf_path = Path(explicit_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"No such file: {pdf_path}")
        return pdf_path
    candidates = sorted(RAW_DIR.glob("*.pdf"))
    if not candidates:
        raise FileNotFoundError(
            f"No PDF found in {RAW_DIR}. Place the confirmed source document there first "
            "(see data/raw/README.md) — this pipeline does not invent a source document."
        )
    if len(candidates) > 1:
        raise RuntimeError(f"Multiple PDFs in {RAW_DIR}: {[p.name for p in candidates]}. Pass --pdf.")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", default=None)
    parser.add_argument("--no-ocr", action="store_true")
    args = parser.parse_args()

    pdf_path = find_source_pdf(args.pdf)
    sha256 = compute_sha256(pdf_path)
    metadata = json.loads(SOURCE_METADATA_PATH.read_text(encoding="utf-8"))
    if metadata.get("sha256") and metadata["sha256"] != sha256:
        raise RuntimeError(
            f"SHA-256 mismatch for {pdf_path.name}: metadata says {metadata['sha256']}, file is {sha256}. "
            "data/raw/ is immutable — log this in RESEARCH_LOG.md instead of overwriting."
        )
    if not metadata.get("sha256"):
        metadata.update({"filename": pdf_path.name, "sha256": sha256})
        SOURCE_METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[extract] {pdf_path.name}  sha256={sha256[:16]}…  (verified against metadata)")

    pages = extract_document(pdf_path, run_ocr=not args.no_ocr)
    save_pages(pages, INTERIM_DIR / "pages.jsonl")

    tables_dir = INTERIM_DIR / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    n_tables = 0
    for p in pages:
        for t_idx, rows in enumerate(p.tables, start=1):
            with open(tables_dir / f"p{p.page_number:03d}_t{t_idx}.csv", "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows(rows)
            n_tables += 1

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    with open(TABLES_DIR / "extraction_log.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["page", "extraction_method", "used_ocr", "words", "blocks", "images", "tables", "ocr_figures", "ocr_figure_words"])
        for p in pages:
            w.writerow([p.page_number, p.extraction_method, p.used_ocr, len(p.text.split()),
                        len(p.blocks), p.n_images, len(p.tables), len(p.figures), sum(len(f["ocr_text"].split()) for f in p.figures)])

    methods = {}
    for p in pages:
        methods[p.extraction_method] = methods.get(p.extraction_method, 0) + 1
    print(f"[extract] {len(pages)} pages; methods={methods}; tables={n_tables}")
    print(f"[extract] wrote {INTERIM_DIR / 'pages.jsonl'} and {TABLES_DIR / 'extraction_log.csv'}")


if __name__ == "__main__":
    main()
