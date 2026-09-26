"""PDF extraction.

Extraction preference order (see documents/methodology.md):
    1. PyMuPDF (fitz)      - fast, good layout/text fidelity
    2. pdfplumber          - fallback, better table handling in some PDFs
    3. OCR (pytesseract)   - only for pages with no extractable text layer

This module must never silently substitute or mutate the file in
`data/raw/`; it only reads from there.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PageExtraction:
    """Raw extraction result for a single page."""

    page_number: int  # 1-indexed, matches the physical document
    text: str
    used_ocr: bool = False
    tables: list = field(default_factory=list)
    extraction_method: str = "pymupdf"  # "pymupdf" | "pdfplumber" | "ocr"


def compute_sha256(file_path: Path) -> str:
    """Compute the SHA-256 hash of a file, used for provenance tracking in
    documents/source_metadata.json. Must be run on the untouched original.
    """
    import hashlib

    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_with_pymupdf(pdf_path: Path) -> list[PageExtraction]:
    """Extract text per page using PyMuPDF. Preferred first pass.

    TODO: implement once the source document is available in data/raw/.
    """
    raise NotImplementedError(
        "PyMuPDF extraction not yet implemented — awaiting confirmed source "
        "document in data/raw/ (see documents/source_metadata.json)."
    )


def extract_with_pdfplumber(pdf_path: Path) -> list[PageExtraction]:
    """Fallback extraction using pdfplumber, e.g. for pages where PyMuPDF
    text ordering looks unreliable or tables need to be captured.

    TODO: implement once the source document is available.
    """
    raise NotImplementedError("pdfplumber extraction not yet implemented.")


def extract_with_ocr(pdf_path: Path, page_number: int) -> PageExtraction:
    """OCR fallback for a page with no extractable text layer.

    Must only be invoked when both PyMuPDF and pdfplumber return an empty
    (or near-empty) text layer for that page — this should be logged, since
    OCR output is lower fidelity and must be flagged in the corpus.

    TODO: implement once the source document is available.
    """
    raise NotImplementedError("OCR extraction not yet implemented.")


def extract_document(pdf_path: Path) -> list[PageExtraction]:
    """Top-level extraction entry point: tries PyMuPDF, falls back to
    pdfplumber, and falls back to OCR per-page when no text layer exists.

    TODO: implement the fallback chain and per-page method logging once the
    source document is available in data/raw/.
    """
    raise NotImplementedError(
        "Document extraction pipeline not yet implemented. This is expected "
        "at the scaffolding stage — see scripts/extract_document.py and "
        "RESEARCH_LOG.md."
    )
