"""AI-authorship / linguistic-provenance analysis module (exploratory).

Per documents/methodology.md and RQ6/RQ7: this module produces stylometric
and (optionally) AI-detector signals about the document, framed strictly as
probabilistic, descriptive linguistic patterns. It must NEVER be used to
assert direct AI authorship (e.g. "written by ChatGPT") or a percentage
figure (e.g. "67% AI-generated") without independent provenance evidence
(metadata, version history, prompt logs, author acknowledgement — see
documents/methodology.md §33 "Gold-standard evidence for AI use").

Allowed conclusion phrasing (§32):
    "Estos segmentos presentan diferencias estilísticas respecto al resto
    del documento."
    "El clasificador X marcó estos segmentos como compatibles con
    generación mediante LLM."
    "El detector presentó una tasa de falsos positivos de X en nuestro
    corpus de control."
    "No existe evidencia suficiente para atribuir estos segmentos de
    manera concluyente a una herramienta de IA."

Disallowed:
    "ChatGPT escribió esta página."
    "El informe fue escrito en un 67% por inteligencia artificial."
"""

from __future__ import annotations

import pandas as pd

from src.config import STYLOMETRY_SEGMENTS_SCHEMA

SEGMENT_WORD_COUNT_RANGE = (500, 1000)  # per documents/methodology.md §23.1


def build_empty_segments_table() -> pd.DataFrame:
    return pd.DataFrame(columns=STYLOMETRY_SEGMENTS_SCHEMA)


def segment_document(corpus_df: pd.DataFrame,
                      target_words: tuple[int, int] = SEGMENT_WORD_COUNT_RANGE) -> pd.DataFrame:
    """Split the corpus into comparable segments of ~500-1000 words each,
    keeping segment_id, pages, section, word_count, raw_text.

    TODO: implement once the corpus exists.
    """
    raise NotImplementedError("Document segmentation not yet implemented.")


def compute_stylometric_features(segments_df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-segment stylometric features: average/variance of
    sentence length, word-length distribution, type-token ratio (and moving
    average TTR), hapax legomena rate, function-word frequencies,
    punctuation frequency, paragraph length, POS distribution,
    dependency-depth proxies, readability, lexical density, stopword
    distribution, first-person usage, passive constructions, connectors,
    transition phrases, modal verbs, hedging language, certainty language.

    TODO: implement using spaCy's Spanish pipeline once dependencies and
    the corpus are available.
    """
    raise NotImplementedError("Stylometric feature computation not yet implemented.")


def analyse_internal_consistency(features_df: pd.DataFrame) -> dict:
    """Compare segments pairwise/sequentially using cosine similarity,
    Jensen-Shannon divergence, Mahalanobis distance, and change-point
    detection to flag statistically notable stylistic shifts.

    IMPORTANT: a detected shift does not by itself indicate AI use — it may
    reflect different authors, editors, source material, sections,
    copyediting, quotations, or technical language (documents/methodology.md
    §23.3). This function must return shifts as flagged locations only, with
    no causal label attached.

    TODO: implement using scipy/sklearn.
    """
    raise NotImplementedError("Internal stylistic consistency analysis not yet implemented.")


def run_detector_calibration_experiment(corpus_a_human, corpus_b_ai, corpus_c_hybrid) -> dict:
    """Run the mandatory calibration experiment (documents/methodology.md
    §23.5) BEFORE any AI detector is applied to the actual report. Computes
    precision, recall, specificity, false-positive rate, false-negative
    rate, F1, and ROC-AUC per detector on Spanish-language control corpora.

    A detector may only be used on the report's segments after this
    function has produced and logged calibration metrics for it (see
    RESEARCH_LOG.md).

    TODO: implement once control corpora A/B/C have been assembled.
    """
    raise NotImplementedError("Detector calibration experiment not yet implemented.")


def apply_calibrated_detector(segments_df: pd.DataFrame, detector_name: str,
                               calibration_metrics: dict) -> pd.DataFrame:
    """Apply a detector to report segments ONLY after calibration metrics
    exist for it. Records detector, version, date, segment, score,
    language, and limitations per documents/methodology.md §23.4. Refuses
    to run (raises) if calibration_metrics is empty/missing.

    TODO: implement.
    """
    if not calibration_metrics:
        raise ValueError(
            "Refusing to apply an uncalibrated detector. Run "
            "run_detector_calibration_experiment() first — see "
            "documents/methodology.md §23.5."
        )
    raise NotImplementedError("Detector application not yet implemented.")
