"""Text preprocessing: normalisation, segmentation, tokenisation, lemmatisation.

Applies to Spanish-language text primarily. The corpus always retains
`raw_text` alongside `clean_text` and `lemma_text` — preprocessing never
destroys the original extracted text (see documents/methodology.md).
"""

from __future__ import annotations

import re
import unicodedata


def normalise_unicode(text: str) -> str:
    """NFC-normalise text and collapse encoding artefacts from PDF extraction
    (e.g. ligatures, stray control characters) without altering wording.
    """
    return unicodedata.normalize("NFC", text)


def detect_headers_and_footers(pages: list[str], min_repetitions: int = 3) -> set[str]:
    """Identify lines that repeat near-identically across many pages (running
    headers/footers, page numbers) so they can be documented and stripped
    rather than silently vanishing from the corpus.

    Returns the set of repeated header/footer strings found. Every removal
    must be logged (see RESEARCH_LOG.md) — this is a traceable transformation,
    not a silent deletion.

    TODO: implement once real page text is available.
    """
    raise NotImplementedError("Header/footer detection not yet implemented.")


def segment_sentences(text: str, language: str = "es") -> list[str]:
    """Split cleaned text into sentences.

    TODO: back this with a proper sentence segmenter (e.g. spaCy's
    Spanish pipeline) rather than a naive regex once dependencies are
    installed and the corpus exists.
    """
    raise NotImplementedError("Sentence segmentation not yet implemented.")


def tokenize(text: str, language: str = "es") -> list[str]:
    """Tokenise text (word-level), preserving proper nouns and quoted spans
    as single-unit candidates for downstream NER/claim extraction.

    TODO: implement using spaCy's es_core_news_lg pipeline.
    """
    raise NotImplementedError("Tokenisation not yet implemented.")


def lemmatize(tokens: list[str], language: str = "es") -> list[str]:
    """Lemmatise a token list.

    TODO: implement using spaCy's es_core_news_lg pipeline.
    """
    raise NotImplementedError("Lemmatisation not yet implemented.")


SPANISH_STOPWORDS_NOTE = (
    "Spanish stopwords are sourced from spaCy's es_core_news_lg default list, "
    "extended with document-specific boilerplate (e.g. repeated headers) "
    "identified via detect_headers_and_footers(). The extension list, once "
    "defined, will be version-controlled here, not hardcoded silently."
)


def preserve_quotes(text: str) -> list[str]:
    """Extract quoted spans (e.g. «...», "...", '...') so they can be
    treated as attributed speech rather than the document's own voice during
    sentiment/framing analysis.

    TODO: implement once real text is available.
    """
    raise NotImplementedError("Quote preservation not yet implemented.")
