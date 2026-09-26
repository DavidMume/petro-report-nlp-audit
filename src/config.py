"""Central configuration: paths, constants, and schema definitions shared
across the pipeline. No analysis logic lives here — only paths and schemas,
so every module agrees on where things live and what columns they contain.
"""

from __future__ import annotations

from pathlib import Path

# --- Paths -------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"

DOCUMENTS_DIR = ROOT_DIR / "documents"
SOURCE_METADATA_PATH = DOCUMENTS_DIR / "source_metadata.json"

OUTPUTS_DIR = ROOT_DIR / "outputs"
TABLES_DIR = OUTPUTS_DIR / "tables"
CHARTS_DIR = OUTPUTS_DIR / "charts"
NETWORKS_DIR = OUTPUTS_DIR / "networks"
REPORTS_DIR = OUTPUTS_DIR / "reports"
DATA_MANIFEST_PATH = OUTPUTS_DIR / "data_manifest.json"

SOURCES_DIR = ROOT_DIR / "sources"
SOURCE_REGISTRY_PATH = SOURCES_DIR / "source_registry.csv"
EVIDENCE_LEDGER_PATH = SOURCES_DIR / "evidence_ledger.csv"

CORPUS_PARQUET_PATH = PROCESSED_DIR / "corpus.parquet"
CORPUS_CSV_PATH = PROCESSED_DIR / "corpus.csv"
CLAIMS_PATH = PROCESSED_DIR / "claims.csv"
CLAIM_EVIDENCE_PATH = PROCESSED_DIR / "claim_evidence.csv"
CLAIM_ASSESSMENTS_PATH = PROCESSED_DIR / "claim_assessments.csv"
NUMERIC_CLAIMS_PATH = PROCESSED_DIR / "numeric_claims.csv"
STYLOMETRY_SEGMENTS_PATH = PROCESSED_DIR / "stylometry_segments.csv"

RESEARCH_LOG_PATH = ROOT_DIR / "RESEARCH_LOG.md"

# --- Language ------------------------------------------------------------

DEFAULT_LANGUAGE = "es"
SPACY_MODEL_ES = "es_core_news_lg"

# --- Corpus schema ---------------------------------------------------------
# Minimum columns preserved for every unit of text extracted from the PDF.
# Every downstream analytical result must be traceable back to these fields.
CORPUS_SCHEMA = [
    "document_id",
    "page",
    "section",
    "paragraph_id",
    "sentence_id",
    "raw_text",
    "clean_text",
    "lemma_text",
]

# --- Claims schema ---------------------------------------------------------
CLAIMS_SCHEMA = [
    "claim_id",
    "claim_text",
    "short_quote",
    "page",
    "section",
    "claim_type",
    "subject",
    "predicate",
    "object",
    "time_period",
    "numeric_value",
    "unit",
    "source_cited_in_report",
    "verifiable",
    "verification_status",
    "confidence",
    "notes",
]

CLAIM_TYPES = [
    "economico",
    "fiscal",
    "empleo",
    "seguridad",
    "salud",
    "energia",
    "instituciones",
    "corrupcion",
    "politica_social",
    "infraestructura",
    "relaciones_internacionales",
    "otros",
]

# --- Claim evidence / assessment schemas ------------------------------------
CLAIM_EVIDENCE_SCHEMA = [
    "claim_id",
    "source_id",
    "source_name",
    "source_url",
    "source_type",
    "publication_date",
    "access_date",
    "evidence_excerpt",
    "supports",
    "contradicts",
    "contextualises",
    "reliability_notes",
]

CLAIM_ASSESSMENTS_SCHEMA = ["claim_id", "assessment", "confidence", "reasoning_summary"]

VERIFICATION_STATUSES = [
    "supported",
    "mostly_supported",
    "mixed_or_disputed",
    "misleading_without_context",
    "unsupported",
    "contradicted",
    "not_independently_verifiable",
    "opinion_or_interpretation",
]

# --- Numeric claims / cross-validation schema -------------------------------
NUMERIC_CLAIMS_SCHEMA = [
    "claim_id",
    "variable",
    "reported_value",
    "reported_unit",
    "reported_period",
    "reported_geography",
    "reported_source",
    "independent_dataset",
    "independent_variable",
    "reconstructed_value",
    "difference_absolute",
    "difference_percent",
    "method",
    "notes",
]

# --- Entities schema ---------------------------------------------------------
ENTITIES_SCHEMA = ["entity", "entity_type", "count", "pages", "sections"]
ENTITY_TYPES = ["PERSON", "ORG", "GPE", "LOC", "DATE", "MONEY", "PERCENT", "LAW"]

# --- Evidence ledger schema --------------------------------------------------
EVIDENCE_LEDGER_SCHEMA = [
    "source_id",
    "title",
    "organisation",
    "author",
    "url",
    "publication_date",
    "access_date",
    "source_type",
    "claim_ids",
    "primary_or_secondary",
    "downloaded_file",
    "sha256",
    "notes",
]

# --- Source-quality hierarchy (see documents/methodology.md) ----------------
SOURCE_PRIORITY = [
    "raw_official_dataset",
    "official_statistical_publication",
    "legislation_or_official_document",
    "peer_reviewed_research",
    "multilateral_organisation",
    "independent_research",
    "reputable_journalism",
    "commentary",
    "social_media",
]

# --- Stylometry segment schema (authorship analysis, exploratory) ----------
STYLOMETRY_SEGMENTS_SCHEMA = ["segment_id", "pages", "section", "word_count", "raw_text"]
