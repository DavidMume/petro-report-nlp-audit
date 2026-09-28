"""Named entity recognition, conservative alias normalisation, and entity /
concept co-occurrence networks.

Sources of entity mentions
--------------------------
- spaCy `es_core_news_lg` NER: PER -> PERSON, ORG -> ORG, LOC -> GPE_LOC,
  MISC -> MISC (MISC is kept in the tables but excluded from charts/networks
  because it is noisy for this genre).
- Regex extractors for types spaCy's Spanish model does not produce:
  DATE, MONEY, PERCENT, LAW (laws, decrees, resolutions, court rulings,
  CONPES documents).

Alias normalisation is deliberately conservative:
1. surface clean-up (whitespace, quotes, leading articles, trailing punctuation);
2. acronym <-> long-form pairs ONLY when the document itself defines them,
   e.g. "Unidad Nacional de Protección (UNP)". Every merge is written to
   outputs/tables/entity_aliases.csv. Ambiguous short forms (e.g.
   "Contraloría", which may be national or territorial) are never merged.
"""

from __future__ import annotations

import itertools
import json
import re
from collections import Counter, defaultdict

import pandas as pd

SPACY_LABEL_MAP = {"PER": "PERSON", "ORG": "ORG", "LOC": "GPE_LOC", "MISC": "MISC"}

MONTHS = "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre"
DATE_RE = re.compile(
    rf"\b(?:\d{{1,2}}º?\s+de\s+(?:{MONTHS})(?:\s+de\s+\d{{4}})?"
    rf"|(?:{MONTHS})\s+(?:de|del)\s+\d{{4}}"
    rf"|(?:entre|desde)\s+(?:(?:{MONTHS})\s+(?:de\s+)?)?\d{{4}}\s+(?:y|hasta|a)\s+(?:(?:{MONTHS})\s+(?:de\s+)?)?\d{{4}}"
    rf"|\d{{4}}\s*[-–]\s*\d{{4}}"
    rf"|(?:19|20)\d{{2}})\b",
    re.I,
)
MONEY_RE = re.compile(
    r"(?:US\$|USD|\$)\s?\d[\d.,]*\s*(?:billones|billón|millones|millón|mil millones|mil)?(?:\s+de\s+(?:pesos|dólares))?"
    r"|\b\d[\d.,]*\s*(?:billones|millones|mil millones)\s+de\s+(?:pesos|dólares)",
    re.I,
)
PERCENT_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s?%|\b\d+(?:[.,]\d+)?\s+por\s+ciento\b", re.I)
LAW_RE = re.compile(
    r"\b(?:Ley|Decreto|Resolución|Circular|Directiva|Acuerdo|Ordenanza)\s+(?:No\.?\s*|número\s+)?\d[\d.]*"
    r"(?:\s+de\s+\d{4})?"
    r"|\bSentencia\s+[A-Z]{1,2}-?\s?\d+(?:\s+de\s+\d{4})?"
    r"|\bCONPES\s+\d+"
    r"|\bActo\s+Legislativo\s+\d+(?:\s+de\s+\d{4})?"
    r"|\bLey\s+de\s+(?:Garantías|Presupuesto|Transparencia|Financiamiento)\b",
    re.I,
)
ACRONYM_DEF_RE = re.compile(r"([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ,.\- ]{3,120}?)\s*\(([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9&\-\.]{1,14})\)")

PUBLIC_INSTITUTION_CUES = [
    "ministerio", "ministra", "ministro", "superintendencia", "agencia", "unidad", "instituto",
    "departamento administrativo", "contraloría", "procuraduría", "fiscalía", "consejo de estado",
    "corte", "registraduría", "policía", "ejército", "armada", "fuerza aérea", "fuerzas militares",
    "fondo", "banco de la república", "presidencia", "vicepresidencia", "congreso", "senado",
    "cámara de representantes", "gobierno", "dane", "dnp", "dian", "sena", "icbf", "invías", "ani",
    "ungrd", "unp", "dapre", "upme", "anh", "creg", "adres", "fontur", "prosperidad social",
    "colpensiones", "ecopetrol", "cancillería", "migración colombia", "defensoría", "comisión",
    "consejo", "tribunal", "juzgado", "gobernación", "alcaldía", "hospital", "empresa social del estado",
    "e.s.p", "servicio geológico", "ideam", "parques nacionales", "sgr", "ocad", "rtvc", "canal trece",
    "codaltec", "electrohuila", "essmar", "fenoge", "cenit", "fonigualdad", "andje", "adr",
    "equipo élite", "autoridad nacional", "colombia compra eficiente", "sociedad de activos especiales",
    "minciencias", "mintic", "minsalud", "mineducación", "minhacienda", "fiduprevisora",
]

_LEADING_ARTICLE_RE = re.compile(r"^(?:el|la|los|las|del|al|de la|de los|de las|de)\s+", re.I)

# Single generic nouns that spaCy tags as entities but that do not identify a
# specific actor ("el Estado", "el Gobierno", "el Ministerio"). They are kept
# in entity_mentions.csv but typed GENERIC and excluded from charts/networks.
GENERIC_TERMS = {
    "estado", "gobierno", "ministerio", "nación", "república", "presidente", "presidencia",
    "entidad", "entidades", "sector", "resolución", "decreto", "energía", "fondo", "agencia",
    "superintendencia", "unidad", "consejo", "equipo", "comité", "ministra", "ministro",
    "patria", "caso", "casos", "capítulo", "libro",
    # fragments of ministry names that spaCy splits off as locations
    "minas", "industria", "ciudad", "empalme", "comercio", "hacienda", "turismo", "cultura", "salud",
    "trabajo", "deporte", "transporte", "vivienda", "territorio", "interior", "justicia", "derecho",
    "educación", "ambiente", "agricultura", "crédito público", "desarrollo rural",
}

# Manual type corrections for recurrent spaCy errors, reviewed by reading the
# mentions in context (entity_mentions.csv). Applied after NER, logged in the
# `source` column as "spacy+override".
TYPE_OVERRIDES = {
    "Niño": "MISC",  # "fenómeno de El Niño"
    "Air-e": "ORG",
    "MinCiencias": "ORG",
    "CAMPETROL": "ORG",
    "Empalme": "GENERIC",
}


def clean_surface(text: str) -> str:
    t = re.sub(r"\s+", " ", text).strip(" \t\n.,;:«»“”\"'()[]")
    t = _LEADING_ARTICLE_RE.sub("", t)
    return t.strip()


def is_public_institution(name: str) -> bool:
    low = name.lower()
    return any(re.search(rf"(?<![\w]){re.escape(c)}(?![\w])", low) for c in PUBLIC_INSTITUTION_CUES)


STOP_INITIAL = {"de", "del", "la", "las", "los", "el", "y", "e", "para", "en", "a", "al", "por"}


def _initials(ws: list[str]) -> str:
    return "".join(w[0].upper() for w in ws if w.lower() not in STOP_INITIAL)


def find_acronym_definitions(texts: list[str]) -> pd.DataFrame:
    """Acronym definitions stated in the document itself: 'Long Name (ACR)'.
    The long form is the shortest trailing word sequence whose initials
    (ignoring function words) spell the acronym, preferring one that starts
    with a capitalised word. Pairs that do not match are discarded, so
    unrelated parentheticals are not captured."""
    rows = {}
    for t in texts:
        for m in ACRONYM_DEF_RE.finditer(t):
            acr = m.group(2).strip(".")
            letters = re.sub(r"[^A-ZÁÉÍÓÚÑ]", "", acr.upper())
            if len(letters) < 2:
                continue
            span = m.group(1)
            tokens = list(re.finditer(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+", span))
            matches = [k for k in range(len(tokens))
                       if _initials([x.group(0) for x in tokens[k:]]) == letters
                       and tokens[k].group(0).lower() not in STOP_INITIAL]
            if not matches:
                continue
            caps = [k for k in matches if tokens[k].group(0)[0].isupper()]
            k = min(caps) if caps else max(matches)
            long_form = clean_surface(span[tokens[k].start():])
            rows.setdefault(acr, long_form)
    return pd.DataFrame(sorted(rows.items()), columns=["alias", "canonical"])


def extract_entity_mentions(corpus_df: pd.DataFrame, nlp=None) -> pd.DataFrame:
    """One row per mention: entity (surface-cleaned), entity_type, source,
    sentence_id, paragraph_id, page, section."""
    if nlp is None:
        from src.preprocess import get_nlp
        nlp = get_nlp()
    rows = []
    for (_, r), doc in zip(corpus_df.iterrows(), nlp.pipe(corpus_df.clean_text, batch_size=64)):
        base = {"sentence_id": r.sentence_id, "paragraph_id": r.paragraph_id, "page": r.page,
                "section": r.section, "level2": r.level2}
        spacy_rows = []
        for ent in doc.ents:
            name = clean_surface(ent.text)
            if len(name) < 2 or not any(c.isalpha() for c in name):
                continue
            etype = SPACY_LABEL_MAP.get(ent.label_, ent.label_)
            source = "spacy"
            if name.lower() in GENERIC_TERMS:
                etype = "GENERIC"
            if name in TYPE_OVERRIDES:
                etype, source = TYPE_OVERRIDES[name], "spacy+override"
            spacy_rows.append({"entity": name, "entity_type": etype, "source": source, **base})
        regex_spans = []
        for etype, rx in (("DATE", DATE_RE), ("MONEY", MONEY_RE), ("PERCENT", PERCENT_RE), ("LAW", LAW_RE)):
            for m in rx.finditer(r.clean_text):
                txt = re.sub(r"\s+", " ", m.group(0)).strip(" ,.")
                regex_spans.append(txt.lower())
                rows.append({"entity": txt, "entity_type": etype, "source": "regex", **base})
        # a regex-typed span (LAW, MONEY, ...) wins over a spaCy span covering the same text
        rows.extend(x for x in spacy_rows if not any(x["entity"].lower() in rs or rs in x["entity"].lower()
                                                       for rs in regex_spans if len(rs) > 6))
    return pd.DataFrame(rows)


def normalise_aliases(mentions: pd.DataFrame, alias_map: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply a document-defined alias map (acronym -> long form). Returns
    (mentions with `entity_canonical`, applied-merges log)."""
    m = mentions.copy()
    m["entity_canonical"] = m.entity
    log = []
    if alias_map is not None and len(alias_map):
        amap = dict(zip(alias_map.alias, alias_map.canonical))
        lower_long = {v.lower(): v for v in amap.values()}
        def canon(e: str) -> str:
            if e in amap:
                return amap[e]
            return lower_long.get(e.lower(), e)
        m["entity_canonical"] = m.entity.map(canon)
        changed = m[m.entity != m.entity_canonical]
        for (a, c), n in changed.groupby(["entity", "entity_canonical"]).size().items():
            log.append({"alias": a, "canonical": c, "mentions_merged": int(n),
                        "rule": "acronym defined in document as 'Long form (ACR)'"})
    # Institutions: spaCy sometimes tags them PERSON/MISC; re-label conservatively.
    mask = m.entity_type.isin(["ORG", "MISC", "PERSON", "GPE_LOC"]) & m.entity_canonical.map(is_public_institution)
    m["is_public_institution"] = False
    m.loc[mask, "is_public_institution"] = True
    return m, pd.DataFrame(log, columns=["alias", "canonical", "mentions_merged", "rule"])


def summarise_entities(mentions: pd.DataFrame) -> pd.DataFrame:
    """entities.csv: entity, entity_type, count, pages, sections (+ extras)."""
    g = mentions.groupby(["entity_canonical", "entity_type"])
    out = g.agg(
        count=("sentence_id", "size"),
        pages=("page", lambda s: ";".join(str(p) for p in sorted(set(s)))),
        sections=("level2", lambda s: " | ".join(sorted(set(s)))),
        n_paragraphs=("paragraph_id", "nunique"),
        is_public_institution=("is_public_institution", "max"),
        surface_forms=("entity", lambda s: " | ".join(sorted(set(s)))),
    ).reset_index().rename(columns={"entity_canonical": "entity"})
    return out.sort_values("count", ascending=False).reset_index(drop=True)


def build_entity_cooccurrence_network(mentions: pd.DataFrame, types=("PERSON", "ORG", "GPE_LOC", "LAW"),
                                      window: str = "paragraph_id", min_count: int = 2, min_weight: int = 1):
    """Undirected graph: nodes are entities (canonical) with >= min_count
    mentions; an edge links two entities appearing in the same paragraph
    (the contextual window); weight = number of shared paragraphs."""
    import networkx as nx

    m = mentions[mentions.entity_type.isin(types)]
    counts = m.groupby("entity_canonical").size()
    keep = set(counts[counts >= min_count].index)
    m = m[m.entity_canonical.isin(keep)]
    etype = m.groupby("entity_canonical").entity_type.agg(lambda s: s.mode().iat[0])
    inst = m.groupby("entity_canonical").is_public_institution.max()
    G = nx.Graph()
    for e in keep:
        G.add_node(e, entity_type=str(etype.get(e, "")), count=int(counts[e]),
                   is_public_institution=bool(inst.get(e, False)))
    w = Counter()
    for _, grp in m.groupby(window):
        ents = sorted(set(grp.entity_canonical))
        for a, b in itertools.combinations(ents, 2):
            w[(a, b)] += 1
    for (a, b), n in w.items():
        if n >= min_weight:
            G.add_edge(a, b, weight=int(n))
    G.remove_nodes_from([n for n in list(G.nodes) if G.degree(n) == 0])
    return G


def build_concept_network(corpus_df: pd.DataFrame, terms: list[str], window: str = "sentence",
                          min_weight: int = 3):
    """Concept co-occurrence network over a supplied term list (lemmas):
    two terms are linked when they occur in the same sentence."""
    import networkx as nx

    tset = set(terms)
    freq = Counter()
    w = Counter()
    for t in corpus_df.lemma_text:
        present = sorted(tset & set(t.split()))
        freq.update(present)
        for a, b in itertools.combinations(present, 2):
            w[(a, b)] += 1
    G = nx.Graph()
    for t in terms:
        G.add_node(t, count=int(freq[t]))
    for (a, b), n in w.items():
        if n >= min_weight:
            G.add_edge(a, b, weight=int(n))
    G.remove_nodes_from([n for n in list(G.nodes) if G.degree(n) == 0])
    return G


def graph_to_json(G) -> dict:
    """Node-link JSON for the web app (d3-force style)."""
    import networkx as nx

    comm = {}
    try:
        from networkx.algorithms.community import greedy_modularity_communities

        for i, c in enumerate(greedy_modularity_communities(G, weight="weight")):
            for n in c:
                comm[n] = i
    except Exception:
        pass
    deg = dict(G.degree(weight="weight"))
    nodes = [{"id": n, **{k: v for k, v in d.items()}, "weighted_degree": int(deg[n]),
              "community": comm.get(n, 0)} for n, d in G.nodes(data=True)]
    links = [{"source": a, "target": b, "weight": d.get("weight", 1)} for a, b, d in G.edges(data=True)]
    return {"nodes": nodes, "links": links, "n_nodes": G.number_of_nodes(), "n_edges": G.number_of_edges(),
            "density": round(nx.density(G), 4) if G.number_of_nodes() > 1 else 0}


def save_graph(G, graphml_path, json_path) -> None:
    import networkx as nx

    graphml_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(G, graphml_path)
    json_path.write_text(json.dumps(graph_to_json(G), ensure_ascii=False, indent=1), encoding="utf-8")


def extract_entities(corpus_df: pd.DataFrame) -> pd.DataFrame:
    """Convenience wrapper kept for API compatibility: mentions -> aliases -> summary."""
    mentions = extract_entity_mentions(corpus_df)
    aliases = find_acronym_definitions(corpus_df.clean_text.tolist())
    mentions, _ = normalise_aliases(mentions, aliases)
    return summarise_entities(mentions)
