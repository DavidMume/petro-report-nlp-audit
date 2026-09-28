"""Claim extraction: builds data/processed/claims.csv (CLAIMS_SCHEMA + extra
traceability columns) and data/processed/numeric_claims.csv.

This is a rule-assisted FIRST PASS. Every row is a *candidate*
(`review_status = auto_candidate`). No sentence becomes a definitive claim,
and nothing here says whether a claim is true: `verification_status` stays
`unassessed` until external evidence is recorded in claim_evidence.csv and a
human-reviewed assessment is written to claim_assessments.csv.

Scoring cues (weights in CUE_WEIGHTS): money, percentages, other numbers
(years excluded), dates, comparative / change language, rankings, causal
markers, named institutions, attribution to a source. Sentences with a
score >= FACTUAL_THRESHOLD are factual candidates; sentences without
checkable content but with evaluative or adversarial language are kept as
`evaluative_candidate` (likely `opinion_or_interpretation` after review).
"""

from __future__ import annotations

import json
import re

import pandas as pd

from src import lexicons as lx
from src.config import CLAIM_TYPES, CLAIMS_SCHEMA, NUMERIC_CLAIMS_SCHEMA
from src.entities import DATE_RE, LAW_RE, MONEY_RE, PERCENT_RE

CLAIMS_EXTRA_COLUMNS = [
    "sentence_id", "paragraph_id", "claim_kind", "extraction_score", "priority", "cues",
    "is_causal", "claim_type_rule", "review_status", "chapter", "level2",
]

CUE_WEIGHTS = {"money": 3, "percent": 3, "number": 2, "date": 1, "comparative": 1, "ranking": 1,
               "causal": 1, "institution": 1, "attribution": 1, "law": 1}
FACTUAL_THRESHOLD = 3

COMPARATIVE_RE = re.compile(
    r"\b(más de|menos de|mayor|menor|superior|inferior|aument\w*|disminu\w*|crec\w*|cay[óo]\w*|cae|redujo|"
    r"reducción|increment\w*|duplic\w*|triplic\w*|récord|históric[oa]s?|por primera vez|pasó de|pasaron de|"
    r"frente a|en comparación|respecto (?:a|de|al)|hasta \d)\b", re.I)
RANKING_RE = re.compile(r"\b(?:el|la|los|las) (?:más|mayor(?:es)?|menor(?:es)?|peor(?:es)?|mejor(?:es)?)\b|"
                        r"\bprimer lugar\b|\btop \d+\b|\branking\b", re.I)
INSTITUTION_RE = re.compile(
    r"\b(Contraloría|Procuraduría|Fiscalía|Consejo de Estado|Corte Constitucional|Corte Suprema|"
    r"Superintendencia|DIAN|DANE|DNP|Banco de la República|Ministerio|Congreso|SECOP|SIIF|Registraduría|"
    r"Defensoría|UNGRD|ICBF|UNP|ADRES|Colpensiones|Ecopetrol|ANH|UPME|CREG|Invías|ANI|FONTUR)\b")
SOURCE_RE = re.compile(
    r"\b(según|de acuerdo con|conforme a|con base en|a partir de|datos de|información de|reportes? de|"
    r"cifras de|registros? de|informe de|auditoría de)\s+(?:la |el |los |las )?([^,;:.()]{3,90})", re.I)
INST_ATTR_RE = re.compile(
    r"\b(Contraloría(?: General de la República)?|Procuraduría(?: General de la Nación)?|Fiscalía|Consejo de Estado|"
    r"Corte Constitucional|Superintendencia [A-ZÁÉÍÓÚ][\w ]{2,40}|DIAN|DANE|SECOP|SIIF(?: Nación)?)\b[^.]{0,80}?"
    r"\b(reveló|advirtió|señaló|evidenció|encontró|identificó|registró|reportó|documentó|estableció|"
    r"determinó|constató|alertó|suspendió|ordenó|abrió|profirió|dictó)", re.I)
YEAR_ONLY_RE = re.compile(r"^(?:19|20)\d{2}$")

MULTIPLIERS = {"billones": 1e12, "billón": 1e12, "mil millones": 1e9, "millones": 1e6, "millón": 1e6, "mil": 1e3}
NUM_TOKEN_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)")

# Keyword rules for suggested claim_type (a suggestion for the reviewer).
TYPE_RULES = {
    "economico": r"PIB|econom[ií]a|inflaci[óo]n|inversi[óo]n|exportaci|importaci|producci[óo]n|productiv|comercio|industria|turismo|empresas?\b|crecimiento econ|agropecuari|tierras?\b|hect[áa]reas",
    "corrupcion": r"corrupci|irregular|sobrecost|detrimento|desv[ií]o|fraude|peculado|soborno|hallazgos? (?:fiscal|disciplinari|penal)|sin soportes?|contrataci[óo]n directa|Equipo [ÉE]lite",
    "fiscal": r"presupuest|d[ée]ficit|deuda|TES\b|regal[ií]as|recaudo|billones|caja|vigencias futuras|rezago|reserva presupuestal|Hacienda|fiscal",
    "empleo": r"empleo|desempleo|contratistas?|n[óo]mina|trabajador|planta de personal|prestaci[óo]n de servicios|vacantes|laboral",
    "seguridad": r"seguridad|grupos? armad|criminal|narcotr[áa]fic|homicid|secuestr|extorsi|Ej[ée]rcito|Polic[ií]a|Fuerza|miner[ií]a ilegal|cultivos il[ií]citos|coca|militar",
    "salud": r"salud|EPS\b|hospital|medicament|ADRES|pacientes|cl[ií]nic|vacun",
    "energia": r"energ[ií]a|gas\b|petr[óo]le|Ecopetrol|hidrocarbur|tarifa|el[ée]ctric|UPME|CREG|Air-e|transmisi[óo]n|generaci[óo]n",
    "instituciones": r"Consejo de Estado|Corte|Procuradur|Contralor[ií]a|Fiscal[ií]a|sentencia|demanda|litigi|arbitr|tutela|Congreso|decreto|resoluci[óo]n",
    "politica_social": r"Colombia Mayor|ICBF|subsidio|pobreza|programa social|Prosperidad Social|adultos mayores|ni[ñn]ez|madres|educaci[óo]n|colegio|docentes|maestros|FOMAG|alimentaci[óo]n escolar|PAE\b|ind[ií]gena",
    "infraestructura": r"v[ií]as?\b|carretera|obra|infraestructura|vivienda|Inv[ií]as|ANI\b|puerto|aeropuerto|acueducto|transporte",
    "relaciones_internacionales": r"Canciller[ií]a|pasaporte|embajad|consulad|Migraci[óo]n Colombia|internacional|exterior|Venezuela|Estados Unidos",
}
SECTION_TYPE_HINTS = {
    "Hacienda": "fiscal", "Trabajo": "empleo", "Defensa": "seguridad", "Salud": "salud", "Minas": "energia",
    "Transporte": "infraestructura", "Vivienda": "infraestructura", "Relaciones Exteriores": "relaciones_internacionales",
    "Inclusión Social": "politica_social", "Educación": "politica_social", "Hallazgos en materia de corrupción": "corrupcion",
    "Justicia": "instituciones", "Interior": "instituciones",
}


def build_empty_claims_table() -> pd.DataFrame:
    return pd.DataFrame(columns=CLAIMS_SCHEMA)


def parse_spanish_number(s: str) -> float | None:
    """'1.234.567,8' -> 1234567.8 ; '4,3' -> 4.3 ; '15' -> 15.0"""
    m = NUM_TOKEN_RE.search(s)
    if not m:
        return None
    return float(m.group(1).replace(".", "").replace(",", "."))


MONTHS_SET = {"enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
              "setiembre", "octubre", "noviembre", "diciembre"}


def mask_dates_and_laws(text: str) -> str:
    """Blank out date and legal-reference spans so that '7 de agosto' or
    'Ley 951 de 2005' are not read as quantities."""
    for rx in (LAW_RE, DATE_RE):
        text = rx.sub(lambda m: " " * len(m.group(0)), text)
    return text


def primary_quantity(text: str) -> dict:
    """Pick the most salient quantity in a sentence: money > percent > other
    number (years excluded). Returns value as written, parsed value, unit,
    and a base-unit value for money (COP or USD)."""
    for m in MONEY_RE.finditer(text):
        raw = re.sub(r"\s+", " ", m.group(0)).strip(" ,.")
        val = parse_spanish_number(raw)
        low = raw.lower()
        mult = next((v for k, v in MULTIPLIERS.items() if k in low), 1.0)
        currency = "USD" if ("us$" in low or "usd" in low or "dólares" in low) else "COP"
        scale = next((k for k in MULTIPLIERS if k in low), "")
        return {"raw": raw, "value": val, "unit": f"{currency} {scale}".strip(),
                "value_base": val * mult if val is not None else None, "kind": "money"}
    for m in PERCENT_RE.finditer(text):
        raw = m.group(0).strip()
        return {"raw": raw, "value": parse_spanish_number(raw), "unit": "%", "value_base": None, "kind": "percent"}
    for m in re.finditer(r"\b(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)\s*(billones|millones|mil millones|mil)?\s+"
                         r"(?:de\s+)?([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+)?)", mask_dates_and_laws(text)):
        num = m.group(1)
        if YEAR_ONLY_RE.match(num):
            continue
        val = parse_spanish_number(num)
        mult = MULTIPLIERS.get(m.group(2) or "", 1.0)
        unit_word = m.group(3).split()[0]
        if unit_word in {"de", "del", "y", "a", "en", "que", "por", "con", "para", "la", "el", "los", "las", "un", "una"} | MONTHS_SET:
            unit_word = ""
        return {"raw": m.group(0)[:60], "value": val, "unit": " ".join(x for x in [m.group(2) or "", unit_word] if x),
                "value_base": val * mult if val is not None else None, "kind": "count"}
    return {"raw": "", "value": None, "unit": "", "value_base": None, "kind": ""}


def detect_cues(text: str, numbers_json: str) -> dict:
    from src.preprocess import extract_numbers

    nums = [n for n in extract_numbers(mask_dates_and_laws(text)) if not YEAR_ONLY_RE.match(n.strip())]
    low = text.lower()
    cues = {
        "money": bool(MONEY_RE.search(text)),
        "percent": bool(PERCENT_RE.search(text)),
        "number": bool(nums) and not (MONEY_RE.search(text) or PERCENT_RE.search(text)),
        "date": bool(DATE_RE.search(text)),
        "comparative": bool(COMPARATIVE_RE.search(text)),
        "ranking": bool(RANKING_RE.search(text)),
        "causal": any(re.search(rf"(?<!\w){re.escape(m)}(?!\w)", low)
                      for m in lx.CAUSAL_MARKERS_CORE + lx.CAUSAL_MARKERS_EXTENDED),
        "institution": bool(INSTITUTION_RE.search(text)),
        "attribution": bool(SOURCE_RE.search(text) or INST_ATTR_RE.search(text)),
        "law": bool(LAW_RE.search(text)),
    }
    return cues


def suggest_claim_type(text: str, section: str) -> tuple[str, str]:
    scores = {k: len(re.findall(v, text, re.I)) for k, v in TYPE_RULES.items()}
    best = max(scores.values())
    if best > 0:
        top = [k for k, v in scores.items() if v == best]
        if len(top) == 1:
            return top[0], "keywords"
        for hint, t in SECTION_TYPE_HINTS.items():
            if hint in section and t in top:
                return t, "keywords+section"
        return top[0], "keywords(tie)"
    for hint, t in SECTION_TYPE_HINTS.items():
        if hint in section:
            return t, "section"
    return "otros", "default"


def source_cited(text: str) -> str:
    m = INST_ATTR_RE.search(text)
    if m:
        return m.group(1).strip()
    m = SOURCE_RE.search(text)
    if m:
        return f"{m.group(1)} {m.group(2)}".strip()
    if re.search(r"\[\d+\]", text):
        return "nota al pie del informe"
    return ""


def time_period(text: str) -> str:
    found = []
    for m in DATE_RE.finditer(text):
        t = re.sub(r"\s+", " ", m.group(0)).strip()
        if t not in found:
            found.append(t)
    return "; ".join(found)


def subject_predicate_object(doc) -> tuple[str, str, str]:
    """Heuristic S-P-O from the dependency parse of one sentence (unreviewed)."""
    root = next((t for t in doc if t.dep_ == "ROOT"), None)
    if root is None:
        return "", "", ""
    subj = next((c for c in root.children if c.dep_ in ("nsubj", "nsubj:pass", "csubj")), None)
    obj = next((c for c in root.children if c.dep_ in ("obj", "dobj", "attr", "ccomp", "xcomp")), None)
    if obj is None:
        obj = next((c for c in root.children if c.dep_ == "obl"), None)
    neg = "no " if any(c.dep_ == "advmod" and c.lower_ == "no" for c in root.children) else ""

    def span(t, n=14):
        if t is None:
            return ""
        words = doc[t.left_edge.i: t.right_edge.i + 1].text.split()
        return " ".join(words[:n]) + (" …" if len(words) > n else "")

    return span(subj), neg + root.lemma_, span(obj)


def short_quote(text: str, max_words: int = 25) -> str:
    w = text.split()
    return " ".join(w[:max_words]) + (" …" if len(w) > max_words else "")


def extract_candidate_claims(corpus_df: pd.DataFrame, nlp=None) -> pd.DataFrame:
    """First-pass claim candidates from the analytic corpus (OCR excluded)."""
    if corpus_df is None:
        raise ValueError("corpus_df is required")
    if nlp is None:
        from src.preprocess import get_nlp
        nlp = get_nlp()
    eval_rx = re.compile("|".join(re.escape(w) for w in lx.NEGATIVE + lx.POSITIVE + lx.ADVERSARIAL), re.I)

    rows = []
    for (_, r), doc in zip(corpus_df.iterrows(), nlp.pipe(corpus_df.clean_text, batch_size=64)):
        text = r.clean_text
        if len(text.split()) < 6:
            continue
        cues = detect_cues(text, r.numbers)
        score = sum(CUE_WEIGHTS[k] for k, v in cues.items() if v)
        n_eval = len(eval_rx.findall(text))
        if score >= FACTUAL_THRESHOLD:
            kind = "factual_candidate"
        elif n_eval >= 2 and not (cues["money"] or cues["percent"] or cues["number"]):
            kind = "evaluative_candidate"
        else:
            continue
        ctype, rule = suggest_claim_type(text, r.section)
        s, p, o = subject_predicate_object(doc)
        q = primary_quantity(text) if kind == "factual_candidate" else {"raw": "", "value": None, "unit": ""}
        verifiable = ("yes_candidate" if kind == "factual_candidate" and (cues["money"] or cues["percent"] or cues["number"])
                      and (cues["date"] or cues["institution"] or cues["law"])
                      else "uncertain" if kind == "factual_candidate" else "no_candidate")
        rows.append({
            "claim_text": text,
            "short_quote": short_quote(text),
            "page": int(r.page),
            "section": r.section,
            "claim_type": ctype,
            "subject": s,
            "predicate": p,
            "object": o,
            "time_period": time_period(text),
            "numeric_value": q["value"],
            "unit": q["unit"],
            "source_cited_in_report": source_cited(text),
            "verifiable": verifiable,
            "verification_status": "unassessed",
            "confidence": None,
            "notes": "auto-extracted; requires human review before use",
            "sentence_id": r.sentence_id,
            "paragraph_id": r.paragraph_id,
            "claim_kind": kind,
            "extraction_score": score,
            "priority": "A" if score >= 7 else "B" if score >= 5 else "C",
            "cues": ";".join(k for k, v in cues.items() if v),
            "is_causal": cues["causal"],
            "claim_type_rule": rule,
            "review_status": "auto_candidate",
            "chapter": r.chapter,
            "level2": r.level2,
            "_quantity": q,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=CLAIMS_SCHEMA + CLAIMS_EXTRA_COLUMNS)
    df.insert(0, "claim_id", [f"C{i:04d}" for i in range(1, len(df) + 1)])
    return df


def numeric_claims_table(claims: pd.DataFrame, corpus_df: pd.DataFrame) -> pd.DataFrame:
    """One row per factual candidate with a primary quantity. Reconstruction
    columns are left empty until a claim is checked against an independent
    dataset (see src/validation.py)."""
    rows = []
    for _, c in claims[claims.claim_kind == "factual_candidate"].iterrows():
        q = c["_quantity"]
        if not q.get("raw"):
            continue
        text = c.claim_text
        i = text.find(q["raw"].split()[0]) if q["raw"] else -1
        window = text[max(0, i - 90): i + len(q["raw"]) + 60] if i >= 0 else text[:150]
        rows.append({
            "claim_id": c.claim_id,
            "variable": window.strip(),
            "reported_value": q["raw"],
            "reported_unit": q["unit"],
            "reported_period": c.time_period,
            "reported_geography": "",
            "reported_source": c.source_cited_in_report,
            "independent_dataset": "",
            "independent_variable": "",
            "reconstructed_value": None,
            "difference_absolute": None,
            "difference_percent": None,
            "method": "",
            "notes": f"auto-extracted ({q['kind']}); parsed_value={q['value']}; value_base={q.get('value_base')}",
        })
    return pd.DataFrame(rows, columns=NUMERIC_CLAIMS_SCHEMA)


def classify_claim_type(claim_text: str, section: str = "") -> str:
    return suggest_claim_type(claim_text, section)[0]


assert set(TYPE_RULES) | {"otros"} == set(CLAIM_TYPES), "TYPE_RULES must cover CLAIM_TYPES"
