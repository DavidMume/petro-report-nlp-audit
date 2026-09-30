"""PDF extraction.

Extraction preference order (see documents/methodology.md):
    1. PyMuPDF             - primary: text + per-span font size/bold/bbox
    2. pdfplumber          - fallback text for pages PyMuPDF returns empty,
                             and table detection on every page
    3. OCR (Tesseract spa) - only for pages with no extractable text layer

This module only reads from `data/raw/`; it never modifies the source file.
Output is an intermediate, block-level representation written to
`data/interim/pages.jsonl` (one JSON object per page) that preserves font
metadata so that headings, running headers/footers and footnotes can be
detected downstream in a documented, reversible way.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

MIN_WORDS_FOR_TEXT_LAYER = 5


@dataclass
class Line:
    text: str
    size: float  # max font size in the line (pt)
    bold: bool  # True if >50% of the line's characters are bold
    bbox: tuple  # (x0, y0, x1, y1) in PDF points, origin top-left


@dataclass
class Block:
    block_id: int
    bbox: tuple
    lines: list[Line]
    ocr_repaired: bool = False

    @property
    def text(self) -> str:
        return " ".join(line.text for line in self.lines)

    @property
    def max_size(self) -> float:
        return max((line.size for line in self.lines), default=0.0)


@dataclass
class PageExtraction:
    """Raw extraction result for a single page."""

    page_number: int  # 1-indexed physical page
    width: float
    height: float
    text: str
    blocks: list = field(default_factory=list)
    tables: list = field(default_factory=list)
    figures: list = field(default_factory=list)  # OCR of large raster figures
    repair_log: list = field(default_factory=list)  # blocks re-read by OCR (corrupted glyph encoding)
    used_ocr: bool = False
    extraction_method: str = "pymupdf"  # "pymupdf" | "pdfplumber" | "ocr" | "none"
    n_images: int = 0

    def to_json(self) -> dict:
        d = asdict(self)
        return d


def compute_sha256(file_path: Path) -> str:
    """SHA-256 of a file; used for provenance tracking in
    documents/source_metadata.json. Must be run on the untouched original."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _line_from_spans(spans: list[dict]) -> Line | None:
    text = "".join(s["text"] for s in spans)
    if not text.strip():
        return None
    n_chars = sum(len(s["text"]) for s in spans) or 1
    bold_chars = sum(len(s["text"]) for s in spans if s["flags"] & 16)
    x0 = min(s["bbox"][0] for s in spans)
    y0 = min(s["bbox"][1] for s in spans)
    x1 = max(s["bbox"][2] for s in spans)
    y1 = max(s["bbox"][3] for s in spans)
    return Line(
        text=text.replace("\t", " ").strip(),
        size=round(max(s["size"] for s in spans), 1),
        bold=bold_chars / n_chars > 0.5,
        bbox=(round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)),
    )


def extract_with_pymupdf(pdf_path: Path) -> list[PageExtraction]:
    """Extract every page with PyMuPDF, preserving block/line structure and
    font metadata."""
    import pymupdf

    pages: list[PageExtraction] = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            blocks = []
            for b_idx, b in enumerate(page.get_text("dict")["blocks"]):
                if b.get("type", 0) != 0:
                    continue
                lines = [ln for ln in (_line_from_spans(l["spans"]) for l in b["lines"]) if ln]
                if lines:
                    blocks.append(Block(block_id=b_idx, bbox=tuple(round(v, 1) for v in b["bbox"]), lines=lines))
            pages.append(
                PageExtraction(
                    page_number=i + 1,
                    width=page.rect.width,
                    height=page.rect.height,
                    text=page.get_text(),
                    blocks=blocks,
                    n_images=len(page.get_images()),
                    extraction_method="pymupdf",
                )
            )
    return pages


def extract_with_pdfplumber(pdf_path: Path, page_numbers: list[int] | None = None) -> dict[int, str]:
    """Fallback plain-text extraction with pdfplumber for the given 1-indexed
    pages (all pages if None). Returns {page_number: text}."""
    import pdfplumber

    out = {}
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            if page_numbers is None or (i + 1) in page_numbers:
                out[i + 1] = page.extract_text() or ""
    return out


def extract_tables_with_pdfplumber(pdf_path: Path, min_rows: int = 2, min_cols: int = 2) -> dict[int, list]:
    """Detect ruled tables on every page with pdfplumber.
    Returns {page_number: [table_rows, ...]} for tables with at least
    `min_rows` x `min_cols` non-empty cells."""
    import pdfplumber

    out: dict[int, list] = {}
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            found = []
            for table in page.extract_tables():
                rows = [[(c or "").replace("\n", " ").strip() for c in row] for row in table]
                rows = [r for r in rows if any(r)]
                if len(rows) >= min_rows and max((sum(1 for c in r if c) for r in rows), default=0) >= min_cols:
                    found.append(rows)
            if found:
                out[i + 1] = found
    return out


def extract_with_ocr(pdf_path: Path, page_number: int, lang: str = "spa", dpi: int = 200) -> str:
    """OCR a single page (1-indexed) with Tesseract. Only used for pages with
    no extractable text layer; OCR output is flagged in the corpus."""
    import pymupdf
    import pytesseract
    from PIL import Image

    with pymupdf.open(pdf_path) as doc:
        pix = doc[page_number - 1].get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return pytesseract.image_to_string(img, lang=lang)


def _overlap_ratio(a: tuple, b: tuple) -> float:
    """Intersection area divided by the smaller box's area."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    smaller = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])) or 1.0
    return ix * iy / smaller


def ocr_large_figures(pdf_path: Path, pages: list[PageExtraction], min_area_frac: float = 0.10,
                      lang: str = "spa", dpi: int = 300) -> None:
    """OCR raster images covering at least `min_area_frac` of a page that has
    a text layer. Some figures in the report (e.g. infographics) are embedded
    as images whose text is absent from the PDF text layer; OCR is the only
    way to make them traceable. Results are stored in `page.figures` and
    always flagged as OCR-derived downstream."""
    import pymupdf
    import pytesseract
    from PIL import Image

    with pymupdf.open(pdf_path) as doc:
        for p in pages:
            if p.used_ocr:
                continue  # whole page already OCR'd
            page = doc[p.page_number - 1]
            area = page.rect.width * page.rect.height
            boxes = [tuple(img["bbox"]) for img in page.get_image_info()]
            boxes = [b for b in boxes if (b[2] - b[0]) * (b[3] - b[1]) / area >= min_area_frac]
            # Stacked image layers of one figure share (almost) the same region:
            # the page render of that region composites them, so OCR it once.
            boxes.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
            kept: list[tuple] = []
            for b in boxes:
                if not any(_overlap_ratio(b, k) > 0.8 for k in kept):
                    kept.append(b)
            for x0, y0, x1, y1 in kept:
                pix = page.get_pixmap(dpi=dpi, clip=pymupdf.Rect(x0, y0, x1, y1))
                im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                text = pytesseract.image_to_string(im, lang=lang)
                p.figures.append({"bbox": [round(v, 1) for v in (x0, y0, x1, y1)], "ocr_text": text})


CONTROL_CHARS_RE = __import__("re").compile(r"[\x00-\x08\x0b-\x1f]")


def repair_corrupted_blocks(pdf_path: Path, pages: list[PageExtraction], lang: str = "spa", dpi: int = 300) -> list[dict]:
    """Some text spans use a font whose glyph encoding maps letters to control
    characters (e.g. 'identi\x17icados' for 'identificados' on p. 8). Such
    blocks are re-read with OCR over their own bounding box; the original
    text is kept in the returned log (outputs/tables/ocr_repaired_blocks.csv)."""
    import pymupdf
    import pytesseract
    from PIL import Image

    log = []
    with pymupdf.open(pdf_path) as doc:
        for p in pages:
            for b in p.blocks:
                if not any(CONTROL_CHARS_RE.search(ln.text) for ln in b.lines):
                    continue
                x0, y0, x1, y1 = b.bbox
                pix = doc[p.page_number - 1].get_pixmap(dpi=dpi, clip=pymupdf.Rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2))
                im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                ocr = " ".join(pytesseract.image_to_string(im, lang=lang).split())
                original = " ".join(ln.text for ln in b.lines)
                size, bold = b.lines[0].size, b.lines[0].bold
                b.lines = [Line(text=ocr, size=size, bold=bold, bbox=b.bbox)]
                b.ocr_repaired = True
                log.append({"page": p.page_number, "block_id": b.block_id, "original_text": original, "ocr_text": ocr})
    return log


def extract_document(pdf_path: Path, run_ocr: bool = True) -> list[PageExtraction]:
    """Full extraction chain: PyMuPDF for all pages, pdfplumber fallback for
    pages PyMuPDF returns (near-)empty, OCR for pages where both are empty,
    plus pdfplumber table detection on every page."""
    pages = extract_with_pymupdf(pdf_path)

    empty = [p.page_number for p in pages if len(p.text.split()) < MIN_WORDS_FOR_TEXT_LAYER]
    if empty:
        plumber = extract_with_pdfplumber(pdf_path, empty)
        for p in pages:
            if p.page_number in plumber and len(plumber[p.page_number].split()) >= MIN_WORDS_FOR_TEXT_LAYER:
                p.text = plumber[p.page_number]
                p.extraction_method = "pdfplumber"

    for p in pages:
        if len(p.text.split()) < MIN_WORDS_FOR_TEXT_LAYER:
            if run_ocr:
                try:
                    p.text = extract_with_ocr(pdf_path, p.page_number)
                    p.used_ocr = True
                    p.extraction_method = "ocr"
                except Exception as exc:  # tesseract missing etc.
                    p.extraction_method = f"none ({type(exc).__name__})"
            else:
                p.extraction_method = "none"

    if run_ocr:
        try:
            pages_repair_log = repair_corrupted_blocks(pdf_path, pages)
        except Exception as exc:  # pragma: no cover
            pages_repair_log = []
            print(f"[extract] block repair skipped: {type(exc).__name__}: {exc}")
        for p in pages:
            p.repair_log = [r for r in pages_repair_log if r["page"] == p.page_number]
        try:
            ocr_large_figures(pdf_path, pages)
        except Exception as exc:  # pragma: no cover - tesseract unavailable
            print(f"[extract] figure OCR skipped: {type(exc).__name__}: {exc}")

    tables = extract_tables_with_pdfplumber(pdf_path)
    for p in pages:
        p.tables = tables.get(p.page_number, [])
    return pages


def save_pages(pages: list[PageExtraction], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for p in pages:
            f.write(json.dumps(p.to_json(), ensure_ascii=False) + "\n")


def load_pages(in_path: Path) -> list[dict]:
    with open(in_path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]
