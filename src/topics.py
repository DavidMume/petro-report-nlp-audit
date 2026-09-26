"""Topic modelling via multiple, triangulated approaches, and the
concept-coocurrence network.

Per documents/methodology.md, no single model's topics are presented as
ground truth: each approach's representative terms and example excerpts are
reported side by side, and topics are never auto-labelled/interpreted by
the pipeline itself.
"""

from __future__ import annotations

import pandas as pd


def fit_tfidf_nmf(corpus_df: pd.DataFrame, n_topics: int = 10):
    """TF-IDF + Non-negative Matrix Factorisation topic model.

    TODO: implement using scikit-learn.
    """
    raise NotImplementedError("TF-IDF+NMF topic modelling not yet implemented.")


def fit_lda(corpus_df: pd.DataFrame, n_topics: int = 10):
    """Latent Dirichlet Allocation topic model.

    TODO: implement using gensim.
    """
    raise NotImplementedError("LDA topic modelling not yet implemented.")


def fit_embedding_clusters(corpus_df: pd.DataFrame, n_clusters: int = 10):
    """Multilingual sentence-embedding + clustering (e.g. k-means or
    HDBSCAN) approach to topic discovery.

    TODO: implement using sentence-transformers + scikit-learn/hdbscan.
    """
    raise NotImplementedError("Embedding-cluster topic modelling not yet implemented.")


def fit_bertopic(corpus_df: pd.DataFrame):
    """BERTopic model, used only if it proves stable for this corpus's size
    (documented decision either way in RESEARCH_LOG.md).

    TODO: implement using the bertopic package.
    """
    raise NotImplementedError("BERTopic modelling not yet implemented.")


def build_concept_network(corpus_df: pd.DataFrame, terms: list[str]):
    """Build a concept co-occurrence network from a supplied term list.

    Returns a networkx.Graph, exported to
    outputs/networks/concept_network.graphml.

    TODO: implement once relevant terms have been identified via EDA.
    """
    raise NotImplementedError("Concept network construction not yet implemented.")
