"""Tests for section detection and paragraph merging in src/corpus.py."""

from src.corpus import Segment, _page_for_offset, _split_sector_heading, merge_paragraphs, segment_document


def line(text, size=10.0, bold=False, y=300):
    return {"text": text, "size": size, "bold": bold, "bbox": [72, y, 500, y + size]}


def page(n, blocks):
    return {"page_number": n, "used_ocr": False, "figures": [], "text": "",
            "blocks": [{"lines": b} for b in blocks]}


def test_sector_heading_split():
    assert _split_sector_heading("Sector Ciencia, Tecnología e Innovación Ciencia congelada: la plata existe") == \
        ("Sector Ciencia, Tecnología e Innovación", "Ciencia congelada: la plata existe")
    assert _split_sector_heading("Sector Trabajo") == ("Sector Trabajo", "")


def test_chapters_cases_and_page_level_prescan():
    pages = [
        page(1, [[line("Texto preliminar del documento.")]]),
        page(2, [[line("02", size=170)], [line("COMPORTAMIENTOS", size=28)]]),
        page(3, [[line("1. Destrucción del rigor técnico", size=21, bold=True)],
                 [line("Caso 1. Presidencia de la República", size=15, bold=True)],
                 [line("La entidad ejecutó poco.")]]),
        page(4, [[line("04", size=170)]]),
        # sector page whose heading appears late in the content stream
        page(5, [[line("Cuerpo del sector antes del título.")],
                 [line("Sector Trabajo", size=13, bold=True, y=100)]]),
    ]
    segs, removed = segment_document(pages)
    body = {s.text: s for s in segs if s.block_type == "body"}
    assert body["Texto preliminar del documento."].chapter.startswith("0.")
    s = body["La entidad ejecutó poco."]
    assert s.chapter.startswith("II.") and s.level2.startswith("Comportamiento 1.") and s.level3.startswith("Caso 1.")
    s = body["Cuerpo del sector antes del título."]
    assert s.chapter.startswith("IV.") and s.level2 == "Sector Trabajo"


def test_merge_paragraphs_keeps_page_provenance():
    a = Segment(1, "body", "Una oración que continúa", 10, "C", "L2", "")
    b = Segment(2, "body", "en la página siguiente.", 10, "C", "L2", "")
    c = Segment(2, "body", "Otra idea.", 10, "C", "L2", "")
    merged = merge_paragraphs([a, b, c])
    assert len(merged) == 2
    assert merged[0].text == "Una oración que continúa en la página siguiente."
    assert _page_for_offset(merged[0].parts, 0) == 1
    assert _page_for_offset(merged[0].parts, len("Una oración que continúa") + 2) == 2
