"""Tests for src/preprocess.py."""

import pytest

from src.preprocess import (
    clean_text,
    detect_headers_and_footers,
    extract_numbers,
    is_header_footer,
    join_lines,
    normalise_unicode,
    preserve_quotes,
    spanish_stopwords,
)


def test_normalise_unicode_is_idempotent_and_keeps_accents():
    t = "inflación, tasación, año­"
    assert normalise_unicode(normalise_unicode(t)) == normalise_unicode(t)
    assert "inflación" in normalise_unicode(t) and "­" not in normalise_unicode(t)


def test_join_lines_dehyphenates_only_real_breaks():
    text, n = join_lines(["La contrata-", "ción directa", "Air-", "E opera"])
    assert "contratación directa" in text
    assert "Air- E" in text  # uppercase continuation is not a hyphenation break
    assert n == 1


def test_clean_text_strips_bullets_and_whitespace():
    assert clean_text("•\t  Dirección   del Empalme ") == "Dirección del Empalme"


def _page(n, lines):
    return {"page_number": n, "blocks": [{"lines": [{"text": t, "bbox": [0, y, 100, y + 8], "size": 8, "bold": False}
                                                    for t, y in lines]}]}


def test_header_footer_detection_requires_margin_and_repetition():
    pages = [_page(i, [("EL LIBRO DE LA VERDAD", 50), (f"EL LIBRO DE LA VERDAD / {i}", 744), ("Cuerpo único", 300)])
             for i in range(1, 5)]
    rep = detect_headers_and_footers(pages)
    assert "EL LIBRO DE LA VERDAD / #" in rep
    body = pages[0]["blocks"][0]["lines"][2]
    assert not is_header_footer(body, rep)
    assert is_header_footer(pages[2]["blocks"][0]["lines"][1], rep)


def test_extract_numbers_and_quotes():
    s = "Ejecutó el 4,3% de $15,3 billones y 1.085 contratos según «la entidad»."
    nums = extract_numbers(s)
    assert "4,3%" in nums and any("15,3" in n for n in nums) and "1.085" in nums
    assert preserve_quotes(s) == ["la entidad"]


def test_domain_words_are_not_stopwords():
    sw = spanish_stopwords()
    for w in ("estado", "verdad", "poder"):
        assert w not in sw
    assert "de" in sw and "la" in sw


def test_sentence_segmentation_and_lemmas_keep_proper_nouns():
    spacy = pytest.importorskip("spacy")
    from src.preprocess import get_nlp, lemma_text_from_doc, segment_sentences
    try:
        nlp = get_nlp()
    except OSError:
        pytest.skip("no Spanish spaCy model installed")
    sents = segment_sentences("La Contraloría abrió un proceso. El Ministerio respondió en julio.")
    assert len(sents) == 2
    lem = lemma_text_from_doc(nlp("La Contraloría abrió 3 procesos."))
    assert "Contraloría" in lem and "3" not in lem
