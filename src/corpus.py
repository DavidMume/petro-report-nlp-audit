"""Build and persist the structured corpus (data/processed/corpus.parquet
and corpus.csv) from raw page-level extractions.

Every row must be traceable to document_id, page, section, paragraph_id and
sentence_id — see CORPUS_SCHEMA in src/config.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import CORPUS_CSV_PATH, CORPUS_PARQUET_PATH, CORPUS_SCHEMA


def build_empty_corpus() -> pd.DataFrame:
    """Return an empty DataFrame with the canonical corpus schema — used for
    schema validation in tests and as the starting point before extraction.
    """
    return pd.DataFrame(columns=CORPUS_SCHEMA)


def build_corpus(pages, document_id: str) -> pd.DataFrame:
    """Assemble the sentence-level corpus DataFrame from a list of
    PageExtraction objects (see src/extract.py).

    TODO: implement paragraph/sentence segmentation and section detection
    once the source document is available.
    """
    raise NotImplementedError(
        "Corpus assembly not yet implemented — awaiting source document "
        "and extraction pipeline."
    )


def save_corpus(df: pd.DataFrame, parquet_path: Path = CORPUS_PARQUET_PATH,
                 csv_path: Path = CORPUS_CSV_PATH) -> None:
    """Persist the corpus to both parquet (for fast downstream loading) and
    csv (for human/spreadsheet inspection and diffability in git).
    """
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)


def load_corpus(parquet_path: Path = CORPUS_PARQUET_PATH) -> pd.DataFrame:
    """Load the persisted corpus."""
    if not parquet_path.exists():
        raise FileNotFoundError(
            f"No corpus found at {parquet_path}. Run `make corpus` after "
            "placing the source document in data/raw/."
        )
    return pd.read_parquet(parquet_path)
