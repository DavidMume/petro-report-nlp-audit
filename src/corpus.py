"""Build and persist the structured corpus from the block-level extraction
(data/interim/pages.jsonl).

Outputs
-------
data/processed/paragraphs.{parquet,csv}  one row per paragraph / heading / footnote / figure
data/processed/corpus.{parquet,csv}      one row per sentence (CORPUS_SCHEMA + CORPUS_EXTRA_COLUMNS)
data/processed/sections.csv              section hierarchy with page ranges and word counts
outputs/tables/removed_headers_footers.csv  every running header/footer line removed

Every sentence row carries document_id, page, section, paragraph_id and
sentence_id, so any downstream result can be traced to a page of the PDF.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.config import (
    CH4_SECTOR_NAMES,
    CHAPTER_TITLES,
    CORPUS_CSV_PATH,
    CORPUS_EXTRA_COLUMNS,
    CORPUS_PARQUET_PATH,
    CORPUS_SCHEMA,
    DOCUMENT_ID,
    FRONT_MATTER_LABEL,
    PARAGRAPHS_CSV_PATH,
    PARAGRAPHS_PARQUET_PATH,
    SECTIONS_CSV_PATH,
    TABLES_DIR,
)
from src.preprocess import (
    BULLETS,
    _norm_margin_line,
    clean_text,
    detect_headers_and_footers,
    extract_numbers,
    get_nlp,
    is_header_footer,
    join_lines,
    lemma_text_from_doc,
    preserve_quotes,
)

HEADING_MIN_SIZE = 12.0  # body text is 9.5-11pt; headings 12pt and above
NUMBER_MIN_SIZE = 40.0  # large decorative numerals (chapter / behaviour numbers)
FOOTNOTE_RE = re.compile(r"^\[\d+\]")
CAPTION_RE = re.compile(r"^(Figura|Tabla|Gráfico|Gráfica|Fuente)\b")
CASE_RE = re.compile(r"^Caso\s+(\d+)\.\s*(.*)")
BEHAVIOUR_RE = re.compile(r"^(\d)\.\s+(\S.*)")
TERMINAL_PUNCT = tuple(".!?:;»”\")")

# Block types that carry the document's own prose and are used for NLP by default.
ANALYTIC_BLOCK_TYPES = ["body", "subheading", "list_item", "quote", "footnote", "caption", "figure_ocr"]


@dataclass
class Segment:
    page: int
    block_type: str
    text: str
    size: float
    chapter: str
    level2: str
    level3: str
    is_ocr: bool = False
    y0: float = 0.0
    parts: list = field(default_factory=list)  # [(char_offset, page)] for merged paragraphs


def _line_role(line: dict) -> str:
    text = line["text"].strip()
    if line["size"] >= NUMBER_MIN_SIZE and text.isdigit():
        return "number"
    if line["size"] >= HEADING_MIN_SIZE:
        return "heading"
    if line["bold"] and 10.5 <= line["size"] < HEADING_MIN_SIZE:
        return "subheading"
    return "text"


def _group_lines(lines: list[dict]) -> list[tuple[str, float, list[dict]]]:
    """Group consecutive lines of a block that share a role (and, for
    headings, a font size) into segments."""
    groups: list[tuple[str, float, list[dict]]] = []
    for ln in lines:
        role = _line_role(ln)
        key_size = ln["size"] if role in ("heading", "number") else 0.0
        if groups and groups[-1][0] == role and groups[-1][1] == key_size:
            groups[-1][2].append(ln)
        else:
            groups.append((role, key_size, [ln]))
    return groups


def _split_sector_heading(text: str) -> tuple[str, str]:
    """'Sector Ciencia, Tecnología e Innovación Ciencia congelada: …' ->
    ('Sector Ciencia, Tecnología e Innovación', 'Ciencia congelada: …')."""
    rest = text[len("Sector "):].strip()
    for name in sorted(CH4_SECTOR_NAMES, key=len, reverse=True):
        if rest.lower().startswith(name.lower()):
            return f"Sector {rest[:len(name)]}", rest[len(name):].strip(" :—-")
    return text, ""


def _is_chapter_title_repeat(text: str) -> bool:
    return text.upper().startswith("CAPÍTULO")


def detect_divider_pages(pages: list[dict]) -> dict[int, int]:
    """Chapter divider pages carry a very large numeral ('01'…'05')."""
    out = {}
    for p in pages:
        for b in p["blocks"]:
            for ln in b["lines"]:
                if ln["size"] >= 100 and ln["text"].strip().isdigit():
                    out[p["page_number"]] = int(ln["text"].strip())
    return out


def _page_prescan(page: dict, chapter_no: int) -> tuple[str, str] | None:
    """Some pages place their main heading late in the PDF content stream
    (e.g. the behaviour-definition pages of chapter II and the sector opening
    pages of chapter IV). Find that heading first so the whole page is
    assigned to it. Returns (level2, level3) or None."""
    for b in page["blocks"]:
        lines = b["lines"]
        roles = [_line_role(ln) for ln in lines]
        if chapter_no == 2 and roles and roles[0] == "number":
            title = " ".join(ln["text"].strip() for ln, r in zip(lines[1:], roles[1:]) if r == "heading")
            if title and lines[1]["size"] >= 19:
                return f"Definición del comportamiento {lines[0]['text'].strip()}: {title}", ""
        if chapter_no == 4:
            for i, (ln, r) in enumerate(zip(lines, roles)):
                if r == "heading" and ln["text"].strip().startswith("Sector "):
                    level2, rest = _split_sector_heading(ln["text"].strip())
                    if not rest:
                        rest = " ".join(l2["text"].strip() for l2, r2 in zip(lines[i + 1:], roles[i + 1:]) if r2 == "heading")
                    return level2, rest
    return None


def segment_document(pages: list[dict]) -> tuple[list[Segment], list[dict]]:
    """Walk pages in order, drop running headers/footers (logged), classify
    each text segment and assign it a chapter / level2 / level3 section."""
    repeated = detect_headers_and_footers(pages)
    dividers = detect_divider_pages(pages)
    removed: list[dict] = []
    segments: list[Segment] = []

    chapter_no = 0
    level2 = level3 = ""
    pending_number = ""

    for p in pages:
        pn = p["page_number"]
        if pn in dividers:
            chapter_no = dividers[pn]
            level2, level3, pending_number = "Portadilla del capítulo", "", ""
        chapter = CHAPTER_TITLES.get(chapter_no, FRONT_MATTER_LABEL)
        pre = _page_prescan(p, chapter_no) if pn not in dividers else None
        if pre:
            level2, level3 = pre
            pending_number = ""

        if p.get("used_ocr"):
            txt = clean_text(p["text"])
            if txt:
                segments.append(Segment(pn, "page_ocr", txt, 0.0, chapter, "Cubierta / página sin capa de texto", "", True))
            continue

        for b in p["blocks"]:
            kept = []
            for ln in b["lines"]:
                if is_header_footer(ln, repeated):
                    removed.append({"page": pn, "text": ln["text"], "y0": ln["bbox"][1], "size": ln["size"],
                                    "reason": "running header/footer (margin line repeated on >=3 pages)"})
                else:
                    kept.append(ln)
            for role, size, lines in _group_lines(kept):
                text, _ = join_lines([ln["text"] for ln in lines])
                text = text.strip()
                if not text:
                    continue
                y0 = lines[0]["bbox"][1]

                if role == "number":
                    pending_number = text
                    segments.append(Segment(pn, "heading", text, size, chapter, level2, level3, y0=y0))
                    continue

                if role == "heading":
                    btype = "heading"
                    if _is_chapter_title_repeat(text) or text.isdigit():
                        if _is_chapter_title_repeat(text):
                            level2, level3 = "Introducción del capítulo", ""
                    elif chapter_no == 0:
                        if size >= 16:
                            level2, level3 = text, ""
                        else:
                            level3 = text
                    elif chapter_no == 2:
                        m_case, m_beh = CASE_RE.match(text), BEHAVIOUR_RE.match(text)
                        if m_beh and size >= 20:
                            level2, level3 = f"Comportamiento {text}", ""
                        elif m_case:
                            level3 = text
                        elif pending_number and size >= 19:
                            level2, level3 = f"Definición del comportamiento {pending_number}: {text}", ""
                            pending_number = ""
                        elif size >= 24:
                            level2, level3 = text, ""
                        else:
                            level3 = text
                    elif chapter_no == 3:
                        if CASE_RE.match(text):
                            level2, level3 = text, ""
                        else:
                            level3 = text
                    elif chapter_no == 4:
                        if text.startswith("Sector "):
                            new2, rest = _split_sector_heading(text)
                            if new2 != level2:
                                level2, level3 = new2, rest
                            elif rest:
                                level3 = rest
                        elif not (pre and text == level3):
                            level3 = text
                    else:  # chapters 1 and 5
                        if chapter_no == 5 and size >= 18 and not re.search(r"[a-záéíóúñ]", text):
                            level2, level3 = "Firmas", ""
                        elif size >= 13:
                            level2, level3 = text, ""
                        else:
                            level3 = text
                    if pn in dividers:
                        level2, level3 = "Portadilla del capítulo", ""
                    segments.append(Segment(pn, btype, text, size, chapter, level2, level3, y0=y0))
                    continue

                # non-heading text
                if FOOTNOTE_RE.match(text):
                    btype = "footnote"
                elif CAPTION_RE.match(text):
                    btype = "caption"
                    if text.startswith(("Figura", "Tabla", "Gráfic")):
                        level2, level3 = text, ""
                elif role == "subheading":
                    btype = "subheading"
                elif text[:1] in BULLETS:
                    btype = "list_item"
                elif text[:1] in "“«\"" and text.rstrip()[-1:] in "”»\"":
                    btype = "quote"
                elif _norm_margin_line(text) in repeated:
                    btype = "running_title"  # decorative repeat of a running header outside the margin
                else:
                    btype = "body"
                segments.append(Segment(pn, btype, text, size, chapter, level2, level3, y0=y0))

        for fig in p.get("figures", []):
            txt = clean_text(" ".join(fig["ocr_text"].split()))
            if txt:
                segments.append(Segment(pn, "figure_ocr", txt, 0.0, chapter, level2, level3, True))

    return segments, removed


def merge_paragraphs(segments: list[Segment]) -> list[Segment]:
    """Merge a body segment into the previous one when the previous does not
    end with terminal punctuation (a paragraph broken by a line-level block,
    column or page break) and both belong to the same section. Page
    provenance of each merged part is kept for sentence-level page mapping."""
    merged: list[Segment] = []
    for s in segments:
        s.parts = [(0, s.page)]
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and s.block_type in ("body", "list_item")
            and prev.block_type in ("body", "list_item")
            and (prev.chapter, prev.level2, prev.level3) == (s.chapter, s.level2, s.level3)
            and not prev.text.rstrip().endswith(TERMINAL_PUNCT)
            and (s.text[:1].islower() or s.block_type == "body")
            and s.text[:1] not in BULLETS
        ):
            offset = len(prev.text) + 1
            prev.text = f"{prev.text} {s.text}"
            prev.parts.append((offset, s.page))
            continue
        merged.append(s)
    return merged


def _section_label(chapter: str, level2: str, level3: str) -> str:
    return " > ".join(x for x in (chapter, level2, level3) if x)


def _page_for_offset(parts: list[tuple[int, int]], offset: int) -> int:
    page = parts[0][1]
    for off, pg in parts:
        if offset >= off:
            page = pg
    return page


def build_corpus(pages: list[dict], document_id: str = DOCUMENT_ID):
    """Return (paragraphs_df, sentences_df, removed_df)."""
    segments, removed = segment_document(pages)
    paras = merge_paragraphs(segments)
    nlp = get_nlp()

    para_rows, sent_rows = [], []
    texts = [s.text for s in paras]
    for idx, (s, doc) in enumerate(zip(paras, nlp.pipe(texts, batch_size=64)), start=1):
        pid = f"P{idx:04d}"
        section = _section_label(s.chapter, s.level2, s.level3)
        pages_spanned = sorted({pg for _, pg in s.parts})
        para_rows.append({
            "document_id": document_id,
            "paragraph_id": pid,
            "page": s.page,
            "page_end": pages_spanned[-1],
            "section": section,
            "chapter": s.chapter,
            "level2": s.level2,
            "level3": s.level3,
            "block_type": s.block_type,
            "is_ocr": s.is_ocr,
            "font_size": s.size,
            "raw_text": s.text,
            "clean_text": clean_text(s.text),
            "n_words": len(s.text.split()),
        })
        if s.block_type in ("heading", "page_ocr"):
            continue
        for k, sent in enumerate(doc.sents, start=1):
            raw = sent.text.strip()
            if not raw:
                continue
            sent_rows.append({
                "document_id": document_id,
                "page": _page_for_offset(s.parts, sent.start_char),
                "section": section,
                "paragraph_id": pid,
                "sentence_id": f"{pid}-S{k:02d}",
                "raw_text": raw,
                "clean_text": clean_text(raw),
                "lemma_text": lemma_text_from_doc(sent),
                "chapter": s.chapter,
                "level2": s.level2,
                "level3": s.level3,
                "block_type": s.block_type,
                "is_ocr": s.is_ocr,
                "numbers": json.dumps(extract_numbers(raw), ensure_ascii=False),
                "quotes": json.dumps(preserve_quotes(raw), ensure_ascii=False),
                "n_words": len(raw.split()),
            })

    paragraphs_df = pd.DataFrame(para_rows)
    sentences_df = pd.DataFrame(sent_rows, columns=CORPUS_SCHEMA + CORPUS_EXTRA_COLUMNS)
    removed_df = pd.DataFrame(removed, columns=["page", "text", "y0", "size", "reason"])
    return paragraphs_df, sentences_df, removed_df


def build_sections_table(paragraphs_df: pd.DataFrame) -> pd.DataFrame:
    body = paragraphs_df[paragraphs_df.block_type != "heading"]
    g = body.groupby(["chapter", "level2"], sort=False)
    out = g.agg(page_start=("page", "min"), page_end=("page_end", "max"),
                n_paragraphs=("paragraph_id", "count"), n_words=("n_words", "sum")).reset_index()
    return out


def build_empty_corpus() -> pd.DataFrame:
    return pd.DataFrame(columns=CORPUS_SCHEMA)


def save_corpus(sentences_df: pd.DataFrame, paragraphs_df: pd.DataFrame | None = None,
                removed_df: pd.DataFrame | None = None, parquet_path: Path = CORPUS_PARQUET_PATH,
                csv_path: Path = CORPUS_CSV_PATH) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    sentences_df.to_parquet(parquet_path, index=False)
    sentences_df.to_csv(csv_path, index=False)
    if paragraphs_df is not None:
        paragraphs_df.to_parquet(PARAGRAPHS_PARQUET_PATH, index=False)
        paragraphs_df.to_csv(PARAGRAPHS_CSV_PATH, index=False)
        build_sections_table(paragraphs_df).to_csv(SECTIONS_CSV_PATH, index=False)
    if removed_df is not None:
        TABLES_DIR.mkdir(parents=True, exist_ok=True)
        removed_df.to_csv(TABLES_DIR / "removed_headers_footers.csv", index=False)


def load_corpus(parquet_path: Path = CORPUS_PARQUET_PATH) -> pd.DataFrame:
    if not parquet_path.exists():
        raise FileNotFoundError(f"No corpus at {parquet_path}. Run `make extract corpus` first.")
    return pd.read_parquet(parquet_path)


def load_paragraphs() -> pd.DataFrame:
    if not PARAGRAPHS_PARQUET_PATH.exists():
        raise FileNotFoundError(f"No paragraphs at {PARAGRAPHS_PARQUET_PATH}. Run `make corpus` first.")
    return pd.read_parquet(PARAGRAPHS_PARQUET_PATH)


def analytic(df: pd.DataFrame, include_ocr: bool = False) -> pd.DataFrame:
    """Rows used for NLP: the document's prose (no headings, no cover OCR);
    OCR-derived figure text excluded unless include_ocr=True."""
    out = df[df.block_type.isin(ANALYTIC_BLOCK_TYPES)]
    if not include_ocr:
        out = out[~out.is_ocr]
    return out
