"""Minimal tests for src/extract.py.

At the scaffolding stage (no source document yet in data/raw/), these tests
check the parts of the module that don't require a real PDF: hashing, and
that the not-yet-implemented functions fail loudly rather than silently
returning fabricated data.
"""

import hashlib
from pathlib import Path

import pytest

from src.extract import compute_sha256, extract_document, extract_with_pymupdf


def test_compute_sha256_matches_hashlib(tmp_path: Path):
    sample = tmp_path / "sample.txt"
    content = b"reproducible audit sample content"
    sample.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()
    assert compute_sha256(sample) == expected


def test_compute_sha256_is_stable_across_calls(tmp_path: Path):
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"\x00\x01\x02" * 1000)

    assert compute_sha256(sample) == compute_sha256(sample)


def test_extract_document_not_yet_implemented(tmp_path: Path):
    """Guards against silently fabricating extraction output before the
    source document and extraction logic exist."""
    fake_pdf = tmp_path / "placeholder.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\n%fake")
    with pytest.raises(NotImplementedError):
        extract_document(fake_pdf)


def test_extract_with_pymupdf_not_yet_implemented(tmp_path: Path):
    fake_pdf = tmp_path / "placeholder.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\n%fake")
    with pytest.raises(NotImplementedError):
        extract_with_pymupdf(fake_pdf)
