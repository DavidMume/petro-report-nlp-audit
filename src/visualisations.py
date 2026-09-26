"""Visualisation functions — one per chart listed in documents/methodology.md
§15. Every chart must be regenerable from a script (scripts/build_outputs.py)
and saved into outputs/charts/ or outputs/networks/. Pie charts are avoided
unless there is a specific, documented reason to use one.
"""

from __future__ import annotations

import pandas as pd

CHART_REGISTRY = [
    "document_overview",
    "words_per_section",
    "top_terms",
    "tfidf_terms",
    "top_bigrams",
    "top_trigrams",
    "entity_frequencies",
    "entity_cooccurrence_network",
    "topic_distribution",
    "topics_by_section",
    "semantic_embedding_map",
    "claim_categories",
    "claims_by_section",
    "verification_status_distribution",
    "verification_status_by_claim_type",
    "sources_cited_by_report",
    "sources_used_by_audit",
    "timeline_of_claims",
    "numeric_claims_dashboard",
    "causal_language_analysis",
]


def plot_document_overview(corpus_df: pd.DataFrame, out_path):
    """TODO: implement (pages, words, sections overview)."""
    raise NotImplementedError


def plot_words_per_section(corpus_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError


def plot_top_terms(freq_df: pd.DataFrame, out_path, top_n: int = 25):
    """TODO: implement."""
    raise NotImplementedError


def plot_tfidf_terms(tfidf_df: pd.DataFrame, out_path, top_n: int = 25):
    """TODO: implement."""
    raise NotImplementedError


def plot_ngrams(ngram_df: pd.DataFrame, out_path, n: int = 2, top_n: int = 25):
    """TODO: implement (used for both bigrams and trigrams)."""
    raise NotImplementedError


def plot_entity_frequencies(entities_df: pd.DataFrame, out_path, top_n: int = 25):
    """TODO: implement."""
    raise NotImplementedError


def plot_topic_distribution(topics_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError


def plot_topics_by_section(topics_df: pd.DataFrame, corpus_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError


def plot_semantic_embedding_map(embeddings, labels, out_path):
    """TODO: implement (UMAP 2D scatter; must caption that distance is
    exploratory only)."""
    raise NotImplementedError


def plot_claim_categories(claims_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError


def plot_claims_by_section(claims_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError


def plot_verification_status_distribution(assessments_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError


def plot_verification_status_by_claim_type(claims_df: pd.DataFrame,
                                            assessments_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError


def plot_sources_cited_by_report(claims_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError


def plot_sources_used_by_audit(evidence_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError


def plot_timeline_of_claims(claims_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError


def plot_numeric_claims_dashboard(numeric_claims_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError


def plot_causal_language_analysis(causal_df: pd.DataFrame, out_path):
    """TODO: implement."""
    raise NotImplementedError
