"""Tests for claim extraction helpers and schemas."""

import json

import pandas as pd
import pytest

from src.claims import (
    build_empty_claims_table,
    detect_cues,
    mask_dates_and_laws,
    parse_spanish_number,
    primary_quantity,
    source_cited,
    suggest_claim_type,
)
from src.config import CLAIM_TYPES, CLAIMS_SCHEMA, VERIFICATION_STATUSES


def test_claims_schema_matches_spec():
    assert CLAIMS_SCHEMA == [
        "claim_id", "claim_text", "short_quote", "page", "section", "claim_type", "subject", "predicate",
        "object", "time_period", "numeric_value", "unit", "source_cited_in_report", "verifiable",
        "verification_status", "confidence", "notes",
    ]
    assert list(build_empty_claims_table().columns) == CLAIMS_SCHEMA


def test_claim_types_and_statuses():
    assert {"economico", "fiscal", "empleo", "seguridad", "salud", "energia", "instituciones", "corrupcion",
            "politica_social", "infraestructura", "relaciones_internacionales", "otros"} <= set(CLAIM_TYPES)
    assert "true" not in VERIFICATION_STATUSES and "false" not in VERIFICATION_STATUSES
    assert len(VERIFICATION_STATUSES) == 8


@pytest.mark.parametrize("s,v", [("1.234.567,8", 1234567.8), ("4,3", 4.3), ("15", 15.0), ("$294,5 billones", 294.5)])
def test_parse_spanish_number(s, v):
    assert parse_spanish_number(s) == pytest.approx(v)


def test_primary_quantity_prefers_money_and_scales_units():
    q = primary_quantity("La UNGRD ejecutó el 4,3% de $15,3 billones entre 2022 y 2026.")
    assert q["kind"] == "money" and q["unit"] == "COP billones"
    assert q["value_base"] == pytest.approx(15.3e12)


def test_dates_and_laws_are_not_quantities():
    t = "El 7 de agosto de 2022 se expidió la Ley 1474 de 2011."
    assert primary_quantity(t)["raw"] == ""
    assert "1474" not in mask_dates_and_laws(t)
    cues = detect_cues(t, json.dumps(["7", "2022", "1474", "2011"]))
    assert not cues["number"] and cues["law"] and cues["date"]


def test_source_cited_and_type():
    assert source_cited("Según SIIF Nación II, la ejecución fue baja.").lower().startswith("según siif")
    assert source_cited("La Contraloría General de la República reveló hallazgos.").startswith("Contraloría")
    assert suggest_claim_type("Las EPS intervenidas acumulan deudas con hospitales.", "")[0] == "salud"


def test_extract_candidate_claims_on_tiny_corpus():
    pytest.importorskip("spacy")
    from src.claims import extract_candidate_claims
    from src.preprocess import get_nlp, extract_numbers
    try:
        get_nlp()
    except OSError:
        pytest.skip("no Spanish spaCy model")
    rows = [
        "Entre 2022 y 2026 la entidad ejecutó apenas el 4,3% de $15,3 billones, según SIIF Nación II.",
        "El país merece un gobierno honesto.",
    ]
    df = pd.DataFrame({"clean_text": rows, "numbers": [json.dumps(extract_numbers(r)) for r in rows],
                       "page": [1, 2], "section": ["x", "y"], "sentence_id": ["P1-S01", "P2-S01"],
                       "paragraph_id": ["P1", "P2"], "chapter": ["c", "c"], "level2": ["l", "l"]})
    out = extract_candidate_claims(df)
    assert out.iloc[0].claim_kind == "factual_candidate"
    assert out.iloc[0].verification_status == "unassessed"
    assert out.iloc[0].review_status == "auto_candidate"
