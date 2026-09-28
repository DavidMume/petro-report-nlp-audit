"""Text preprocessing: normalisation, running header/footer detection,
line joining, sentence segmentation, tokenisation, lemmatisation, number and
quote extraction.

The corpus always keeps `raw_text` next to `clean_text` and `lemma_text`;
nothing here overwrites the extracted text, and every removal (running
headers/footers) is returned so it can be logged
(outputs/tables/removed_headers_footers.csv).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache

from src.config import SPACY_MODEL_ES

# --- Normalisation -----------------------------------------------------------

_SOFT_HYPHEN = "­"
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍﻿"), None)
BULLETS = "•●▪◦·–"


def normalise_unicode(text: str) -> str:
    """NFC-normalise, drop soft hyphens / zero-width characters, turn tabs and
    non-breaking spaces into spaces. Wording is never changed."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace(_SOFT_HYPHEN, "").translate(_ZERO_WIDTH)
    text = text.replace("\t", " ").replace(" ", " ").replace(" ", " ")
    return text


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def join_lines(lines: list[str]) -> tuple[str, int]:
    """Join PDF lines into running text. A line ending in a letter + hyphen
    followed by a lowercase-initial line is treated as a typographic
    hyphenation break and re-joined without the hyphen. Returns the text and
    the number of de-hyphenations performed (for the log)."""
    out = ""
    n_dehyphen = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if out.endswith("-") and len(out) > 1 and out[-2].isalpha() and line[:1].islower():
            out = out[:-1] + line
            n_dehyphen += 1
        else:
            out = f"{out} {line}" if out else line
    return out, n_dehyphen


def clean_text(text: str) -> str:
    """Analysis-ready text: normalised, whitespace-collapsed, leading bullet
    glyphs removed. Case, accents, digits and punctuation are preserved."""
    text = collapse_whitespace(normalise_unicode(text))
    text = text.lstrip(BULLETS + " ")
    return text


# --- Running headers / footers ------------------------------------------------

def _norm_margin_line(text: str) -> str:
    return re.sub(r"\d+", "#", collapse_whitespace(normalise_unicode(text))).upper().strip(" /")


def detect_headers_and_footers(pages: list[dict], top_margin: float = 72.0, bottom_margin: float = 735.0,
                               min_repetitions: int = 3) -> set[str]:
    """Return normalised strings (digits replaced by '#') of lines that sit in
    the top/bottom margin and repeat on at least `min_repetitions` pages:
    running titles, section labels and page numbers."""
    seen: dict[str, set[int]] = defaultdict(set)
    for p in pages:
        for b in p["blocks"]:
            for ln in b["lines"]:
                y0 = ln["bbox"][1]
                if y0 < top_margin or y0 > bottom_margin:
                    seen[_norm_margin_line(ln["text"])].add(p["page_number"])
    return {k for k, v in seen.items() if len(v) >= min_repetitions and k}


def is_header_footer(line: dict, repeated: set[str], top_margin: float = 72.0,
                     bottom_margin: float = 735.0) -> bool:
    y0 = line["bbox"][1]
    if not (y0 < top_margin or y0 > bottom_margin):
        return False
    return _norm_margin_line(line["text"]) in repeated


# --- Quotes and numbers -------------------------------------------------------

_QUOTE_RE = re.compile(r"«([^»]{3,})»|“([^”]{3,})”|\"([^\"]{3,})\"")
NUMBER_RE = re.compile(
    r"(?:US?\$|\$|€)?\s?\d{1,3}(?:\.\d{3})+(?:,\d+)?\s?%?"  # 1.234.567,8
    r"|(?:US?\$|\$|€)?\s?\d+(?:,\d+)?\s?%?"  # 4,3 / 15 / 50%
)


def preserve_quotes(text: str) -> list[str]:
    """Quoted spans («…», “…”, "…") — treated as attributed or cited speech
    rather than the document's own voice in framing analysis."""
    return [next(g for g in m.groups() if g) for m in _QUOTE_RE.finditer(text)]


def extract_numbers(text: str) -> list[str]:
    """Numeric expressions (money, percentages, counts, years) kept verbatim
    in a separate column instead of being mixed into lemma_text."""
    return [m.group(0).strip() for m in NUMBER_RE.finditer(text) if any(c.isdigit() for c in m.group(0))]


# --- spaCy -----------------------------------------------------------------------

@lru_cache(maxsize=2)
def get_nlp(model: str = SPACY_MODEL_ES):
    """Load (once) the Spanish spaCy pipeline. Falls back to the md model if
    the lg model is not installed."""
    import spacy

    for name in (model, "es_core_news_lg", "es_core_news_md", "es_core_news_sm"):
        try:
            nlp = spacy.load(name)
            nlp.max_length = 2_000_000
            return nlp
        except OSError:
            continue
    raise OSError("No Spanish spaCy model installed. Run: python -m spacy download es_core_news_lg")


def segment_sentences(text: str, language: str = "es") -> list[str]:
    """Split text into sentences with spaCy's dependency-based segmenter."""
    if not text.strip():
        return []
    return [s.text.strip() for s in get_nlp()(text).sents if s.text.strip()]


def tokenize(text: str, language: str = "es") -> list[str]:
    return [t.text for t in get_nlp()(text) if not t.is_space]


# spaCy's Spanish stopword list contains content words that are central in
# this domain ("Estado", "verdad", "poder", "mayor", "nuevo", "total", ...).
# They are kept (documented decision, RESEARCH_LOG 2026-09-28).
STOPWORD_KEEP = {
    "estado", "estados", "verdad", "poder", "bien", "parte", "mayor", "nuevo", "nueva", "nuevos",
    "nuevas", "gran", "grandes", "total", "primero", "primera", "último", "última", "cierto",
    "fin", "final", "medio", "mejor", "peor", "largo", "cuenta", "propio", "propia",
}


@lru_cache(maxsize=1)
def spanish_stopwords() -> frozenset:
    from spacy.lang.es.stop_words import STOP_WORDS

    return frozenset(w for w in STOP_WORDS if w not in STOPWORD_KEEP)


def lemma_text_from_doc(doc) -> str:
    """Lemmatised, lowercase content words; stopwords, punctuation and
    numbers removed; proper nouns kept in their original form so names are
    not flattened (e.g. 'Petro', 'Contraloría')."""
    out = []
    for t in doc:
        if t.is_space or t.is_punct or t.like_num or not any(c.isalpha() for c in t.text):
            continue
        if t.lower_ in spanish_stopwords():
            continue
        if t.pos_ == "PROPN":
            out.append(t.text)
        else:
            out.append(t.lemma_.lower())
    return " ".join(out)


def lemmatize(tokens: list[str], language: str = "es") -> list[str]:
    return lemma_text_from_doc(get_nlp()(" ".join(tokens))).split()


SPANISH_STOPWORDS_NOTE = (
    "Stopwords: spaCy's Spanish default list minus STOPWORD_KEEP (domain content words). Document-specific "
    "boilerplate is removed as running headers/footers, not via stopwords; the extra "
    "domain stopword list used for term-frequency tables is DOMAIN_STOPWORDS in src/nlp.py."
)


def most_common_margin_lines(pages: list[dict], k: int = 20) -> list[tuple[str, int]]:
    c = Counter()
    for p in pages:
        for b in p["blocks"]:
            for ln in b["lines"]:
                c[_norm_margin_line(ln["text"])] += 1
    return c.most_common(k)
