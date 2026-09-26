"""Exploratory NLP: frequencies, TF-IDF, n-grams, lexical diversity, and
exploratory sentiment/framing/causal-language tagging.

All outputs here are DESCRIPTIVE. None of these functions should be used to
assert that a document is biased, deceptive, or truthful — see
documents/methodology.md §"NLP methodology" and §"Causality".
"""

from __future__ import annotations

import pandas as pd

# Causal-language markers to tag separately from descriptive language
# (documents/methodology.md §"Causality"). Tagging these does NOT imply the
# underlying causal claim is correct or incorrect — it flags language for
# separate methodological review.
CAUSAL_MARKERS_ES = [
    "causó",
    "provocó",
    "generó",
    "produjo",
    "debido a",
    "como consecuencia de",
    "resultado de",
    "gracias a",
    "por culpa de",
]


def compute_basic_stats(corpus_df: pd.DataFrame) -> dict:
    """Pages, words, sentences, mean sentence length, vocabulary size,
    lexical diversity (type-token ratio).

    TODO: implement once a real corpus DataFrame exists.
    """
    raise NotImplementedError("Basic corpus statistics not yet implemented.")


def compute_term_frequencies(corpus_df: pd.DataFrame) -> pd.DataFrame:
    """Absolute and relative term frequency table.

    TODO: implement.
    """
    raise NotImplementedError("Term frequency computation not yet implemented.")


def compute_tfidf(corpus_df: pd.DataFrame) -> pd.DataFrame:
    """TF-IDF matrix / top-terms table (paragraph or section level).

    TODO: implement using scikit-learn's TfidfVectorizer with a
    Spanish-aware tokenizer.
    """
    raise NotImplementedError("TF-IDF computation not yet implemented.")


def compute_ngrams(corpus_df: pd.DataFrame, n: int = 2) -> pd.DataFrame:
    """Bigrams (n=2) / trigrams (n=3) frequency table.

    TODO: implement.
    """
    raise NotImplementedError("N-gram computation not yet implemented.")


def tag_causal_language(corpus_df: pd.DataFrame) -> pd.DataFrame:
    """Flag sentences containing causal-language markers for a dedicated
    review table, kept separate from purely descriptive statements.

    TODO: implement using CAUSAL_MARKERS_ES plus dependency-parse
    verification (to reduce false positives from markers used non-causally).
    """
    raise NotImplementedError("Causal-language tagging not yet implemented.")


def exploratory_sentiment(corpus_df: pd.DataFrame) -> pd.DataFrame:
    """Exploratory sentiment/framing signals: positive/negative lexicon
    hits, modal verbs, certainty/uncertainty language, attribution verbs,
    adversarial framing markers.

    Must be reported with explicit limitations (documents/methodology.md);
    never converted into a single "bias score".

    TODO: implement and document the specific lexicon/model used, plus its
    known limitations for Spanish political-document text.
    """
    raise NotImplementedError("Exploratory sentiment analysis not yet implemented.")
