#!/usr/bin/env python3
"""Build the structured corpus (data/processed/corpus.{parquet,csv}) from
the page-level extraction produced by scripts/extract_document.py.

Usage:
    python scripts/build_corpus.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.corpus import build_corpus, save_corpus


def main() -> None:
    # TODO: load the page-level extraction result once scripts/extract_document.py
    # persists an intermediate artefact to data/interim/, then call
    # build_corpus() + save_corpus(). Left unimplemented at the scaffolding
    # stage — see RESEARCH_LOG.md.
    raise NotImplementedError(
        "build_corpus.py is scaffolded but not yet wired to real extraction "
        "output. Run this after the source document has been placed in "
        "data/raw/ and src/extract.py has been implemented."
    )


if __name__ == "__main__":
    main()
