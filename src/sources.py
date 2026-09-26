"""Source registry and evidence-ledger management, plus the source-quality
priority ordering used when weighing conflicting evidence.

See documents/methodology.md §26-27 and SOURCE_PRIORITY in src/config.py.
"""

from __future__ import annotations

import pandas as pd

from src.config import EVIDENCE_LEDGER_SCHEMA, SOURCE_PRIORITY

# Likely Colombian institutional data sources to consult WHEN a specific
# claim calls for them — never applied automatically/indiscriminately.
LIKELY_COLOMBIAN_SOURCES = [
    "DANE", "Banco de la República", "Ministerio de Hacienda", "DIAN", "DNP",
    "Contraloría General", "Procuraduría", "Fiscalía", "Policía Nacional",
    "Ministerio de Defensa", "Ministerio de Salud", "Ministerio de Educación",
    "UPME", "XM", "ANH", "Superintendencias", "SECOP", "Datos Abiertos Colombia",
    "Congreso de Colombia", "Presidencia",
]

LIKELY_INTERNATIONAL_SOURCES = [
    "World Bank", "IMF", "OECD", "ILO", "WHO", "UNODC", "ECLAC/CEPAL",
]


def build_empty_evidence_ledger() -> pd.DataFrame:
    return pd.DataFrame(columns=EVIDENCE_LEDGER_SCHEMA)


def rank_source_type(source_type: str) -> int:
    """Return the priority rank (lower = higher priority) of a source_type
    string against SOURCE_PRIORITY. Used to flag when a lower-priority
    source is being relied on despite a higher-priority one being available,
    not to auto-resolve conflicts.
    """
    try:
        return SOURCE_PRIORITY.index(source_type)
    except ValueError:
        return len(SOURCE_PRIORITY)  # unranked sources sort last


def register_source(evidence_ledger: pd.DataFrame, **fields) -> pd.DataFrame:
    """Append a new row to the evidence ledger. Requires the caller to
    supply access_date and, where applicable, downloaded_file + sha256 for
    anything saved locally under sources/primary or sources/secondary.

    TODO: add validation once the ledger is in active use.
    """
    raise NotImplementedError("Evidence ledger registration not yet implemented.")
