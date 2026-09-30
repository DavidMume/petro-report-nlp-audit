#!/usr/bin/env python3
"""Build the structured corpus (data/processed/corpus.{parquet,csv},
paragraphs.{parquet,csv}, sections.csv) from data/interim/pages.jsonl.

Usage:
    python scripts/build_corpus.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import PAGES_JSONL_PATH
from src.corpus import build_corpus, save_corpus
from src.extract import load_pages


def main() -> None:
    if not PAGES_JSONL_PATH.exists():
        raise FileNotFoundError(f"{PAGES_JSONL_PATH} missing — run `make extract` first.")
    pages = load_pages(PAGES_JSONL_PATH)
    paragraphs, sentences, removed = build_corpus(pages)
    save_corpus(sentences, paragraphs, removed)
    print(f"[corpus] paragraphs={len(paragraphs)} sentences={len(sentences)} "
          f"removed_header_footer_lines={len(removed)}")
    print(paragraphs.block_type.value_counts().to_string())


if __name__ == "__main__":
    main()
