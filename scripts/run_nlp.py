#!/usr/bin/env python3
"""Run exploratory NLP over the corpus: frequencies, TF-IDF, n-grams,
entities, topics, embeddings, and exploratory sentiment/causal-language
tagging. Writes tables to outputs/tables/ and (via build_outputs.py)
charts to outputs/charts/.

Usage:
    python scripts/run_nlp.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.corpus import load_corpus


def main() -> None:
    corpus_df = load_corpus()  # raises a clear error if corpus.parquet doesn't exist yet
    # TODO: call src.nlp / src.entities / src.topics / src.embeddings
    # functions in sequence once they are implemented, writing results to
    # outputs/tables/. Left unimplemented at the scaffolding stage.
    raise NotImplementedError(
        "run_nlp.py is scaffolded but the analysis functions in src/nlp.py, "
        "src/entities.py, src/topics.py and src/embeddings.py are not yet "
        "implemented — see RESEARCH_LOG.md."
    )


if __name__ == "__main__":
    main()
