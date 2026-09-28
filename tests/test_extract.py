"""Tests for src/extract.py (synthetic PDFs, no dependency on the real source)."""

import hashlib
import shutil
from pathlib import Path

import pytest

from src.extract import _overlap_ratio, compute_sha256, extract_document, extract_with_pymupdf

pymupdf = pytest.importorskip("pymupdf")


def make_pdf(path: Path, pages: list[list[tuple[str, float]]]) -> Path:
    """Each page is a list of (text, fontsize) lines; an empty list makes a blank page."""
    doc = pymupdf.open()
    for lines in pages:
        page = doc.new_page(width=612, height=792)
        y = 100
        for text, size in lines:
            page.insert_text((72, y), text, fontsize=size)
            y += size * 1.8
    doc.save(path)
    return path


def test_compute_sha256_matches_hashlib(tmp_path: Path):
    sample = tmp_path / "sample.txt"
    sample.write_bytes(b"reproducible audit sample content")
    assert compute_sha256(sample) == hashlib.sha256(b"reproducible audit sample content").hexdigest()


def test_pymupdf_extraction_keeps_pages_and_font_sizes(tmp_path: Path):
    pdf = make_pdf(tmp_path / "t.pdf", [[("Titulo grande", 20), ("Texto normal de cuerpo.", 10)],
                                        [("Segunda pagina con texto.", 10)]])
    pages = extract_with_pymupdf(pdf)
    assert [p.page_number for p in pages] == [1, 2]
    sizes = [ln.size for b in pages[0].blocks for ln in b.lines]
    assert max(sizes) >= 19 and min(sizes) <= 11
    assert "Segunda" in pages[1].text


def test_blank_page_without_ocr_is_flagged_not_invented(tmp_path: Path):
    pdf = make_pdf(tmp_path / "t.pdf", [[("Pagina con texto suficiente para la capa.", 10)], []])
    pages = extract_document(pdf, run_ocr=False)
    assert pages[0].extraction_method == "pymupdf"
    assert pages[1].extraction_method == "none"
    assert pages[1].text.strip() == ""


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_blank_page_goes_to_ocr_when_enabled(tmp_path: Path):
    pdf = make_pdf(tmp_path / "t.pdf", [[("Pagina con texto suficiente para la capa.", 10)], []])
    pages = extract_document(pdf, run_ocr=True)
    assert pages[1].used_ocr and pages[1].extraction_method == "ocr"


def test_overlap_ratio():
    assert _overlap_ratio((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert _overlap_ratio((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0
    assert 0.2 < _overlap_ratio((0, 0, 10, 10), (5, 5, 15, 15)) < 0.3
