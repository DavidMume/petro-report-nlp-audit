"""Named entity recognition and entity co-occurrence network construction.

See ENTITIES_SCHEMA in src/config.py for the output table schema, and
documents/methodology.md for alias-normalisation rules (only merge aliases
when reasonably unambiguous; never auto-merge ambiguous entities).
"""

from __future__ import annotations

import pandas as pd

from src.config import ENTITY_TYPES


def extract_entities(corpus_df: pd.DataFrame) -> pd.DataFrame:
    """Run NER (spaCy es_core_news_lg) over the corpus and return one row
    per (entity, entity_type) with count, pages, and sections.

    TODO: implement once the corpus exists and spaCy's Spanish model is
    installed.
    """
    raise NotImplementedError("Entity extraction not yet implemented.")


def normalise_aliases(entities_df: pd.DataFrame, alias_map: dict[str, str] | None = None) -> pd.DataFrame:
    """Apply a documented, human-reviewed alias map (e.g. "Gustavo Petro" /
    "Presidente Petro" / "el presidente" -> canonical form) — never merges
    automatically without a supplied, reviewed mapping.

    TODO: implement once entities have been extracted and manually reviewed.
    """
    raise NotImplementedError("Alias normalisation not yet implemented.")


def build_entity_cooccurrence_network(corpus_df: pd.DataFrame, entities_df: pd.DataFrame,
                                       window: str = "paragraph"):
    """Build a co-occurrence network where two entities are connected if
    they appear within the same paragraph (or a defined contextual window).

    Returns a networkx.Graph. Exported via scripts/build_outputs.py to
    outputs/networks/entity_network.graphml.

    TODO: implement using networkx once entities and corpus are available.
    """
    raise NotImplementedError("Entity co-occurrence network not yet implemented.")
