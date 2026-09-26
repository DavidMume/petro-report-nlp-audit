"""Multilingual embeddings for paragraphs, sections, and claims, plus UMAP
projections for exploratory visualisation only (never treated as an exact
semantic-distance measurement — documents/methodology.md).
"""

from __future__ import annotations

import pandas as pd

DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-mpnet-base-v2"


def embed_texts(texts: list[str], model_name: str = DEFAULT_EMBEDDING_MODEL):
    """Compute sentence-transformer embeddings for a list of texts.

    TODO: implement using sentence-transformers once dependencies are
    installed.
    """
    raise NotImplementedError("Text embedding not yet implemented.")


def embed_paragraphs(corpus_df: pd.DataFrame):
    """Embed at paragraph granularity.

    TODO: implement.
    """
    raise NotImplementedError("Paragraph embedding not yet implemented.")


def embed_sections(corpus_df: pd.DataFrame):
    """Embed at section granularity (mean- or concat-pooled from paragraphs).

    TODO: implement.
    """
    raise NotImplementedError("Section embedding not yet implemented.")


def embed_claims(claims_df: pd.DataFrame):
    """Embed each extracted claim's text.

    TODO: implement.
    """
    raise NotImplementedError("Claim embedding not yet implemented.")


def project_umap(embeddings, n_neighbors: int = 15, min_dist: float = 0.1):
    """2D UMAP projection for exploratory visualisation ONLY. Document
    prominently wherever plotted that 2D distance is not a reliable proxy
    for semantic distance.

    TODO: implement using umap-learn.
    """
    raise NotImplementedError("UMAP projection not yet implemented.")
