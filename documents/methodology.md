# Methodology

This document is the methodological charter for the project. It is written
before any substantive analysis of the source report and is updated as
methodological decisions are made (each such decision is also logged in
`RESEARCH_LOG.md` with its rationale).

## Guiding question

> ¿Qué afirma el informe, cómo construye esas afirmaciones y qué tan bien se
> sostienen cuando se contrastan sistemáticamente con evidencia externa?

This project does **not** set out to prove that the report is true, false,
biased, favourable, or unfavourable to any political figure or
administration, and it does not produce an overall verdict, score, or
rating of the report, its subject, or any government. See
`RESEARCH_LOG.md` §"Editorial neutrality" for the standing rule.

## Three separated problems

1. **What the report says** — descriptive extraction of its claims,
   entities, structure and language.
2. **How it builds its argument** — narrative/rhetorical analysis: framing,
   evaluative language, causal language, structure.
3. **How well its claims hold up against verifiable evidence** — claim
   verification against primary/official sources, with transparent,
   non-binary outcome categories (see `claim_assessments.csv` schema).

These three are tracked and reported **separately** and are never collapsed
into a single score.

## Research questions

- **RQ1.** ¿Cuáles son las principales afirmaciones factuales del informe?
- **RQ2.** ¿Qué temas, personas, instituciones y conceptos reciben mayor
  atención?
- **RQ3.** ¿Qué patrones lingüísticos y narrativos aparecen en el documento?
- **RQ4.** ¿Qué porcentaje de las afirmaciones verificables puede
  contrastarse con evidencia externa disponible?
- **RQ5.** ¿Qué ocurre cuando las principales afirmaciones cuantitativas se
  reconstruyen utilizando datos originales?
- **RQ6.** ¿Existen cambios estilísticos internos compatibles con múltiples
  procesos de escritura, edición o asistencia automatizada?
- **RQ7 (exploratory only).** ¿Existe evidencia lingüística compatible con
  el uso de herramientas de IA generativa durante la preparación del
  documento? This is explicitly **not** framed as "what percentage was
  written by an AI" — current methods cannot establish that with
  scientific certainty. See §"AI authorship analysis" below and
  `src/authorship.py`.

## Document provenance

Handled in `documents/source_metadata.json` and `data/raw/README.md`.
`data/raw/` is treated as immutable; no file there is edited or silently
replaced.

## Corpus construction

The PDF is converted into a structured corpus that preserves, per unit of
text: document ID, page, section, paragraph ID, sentence ID, raw text,
cleaned text, and lemmatised text. Every downstream result must be
traceable back to a specific page of the original document. Extraction
preference: PyMuPDF → pdfplumber → OCR (only for pages without a text
layer). See `src/extract.py`, `src/corpus.py`, `scripts/extract_document.py`,
`scripts/build_corpus.py`.

## NLP methodology

Exploratory, multi-method, and explicitly descriptive rather than
adjudicative:

- Frequency, TF-IDF, n-grams, lexical diversity (`src/nlp.py`).
- Named entity recognition (PERSON, ORG, GPE/LOC, DATE, MONEY, PERCENT, and
  laws/regulations where identifiable) with manual review before merging
  aliases (`src/entities.py`).
- Entity co-occurrence and concept networks (`src/entities.py`,
  `src/topics.py`, exported to `outputs/networks/`).
- Topic modelling using multiple approaches for triangulation — TF-IDF+NMF,
  LDA, multilingual-embedding clustering, and BERTopic where the corpus size
  supports it — with representative terms and example excerpts, not
  auto-labelled topics (`src/topics.py`).
- Multilingual embeddings at paragraph, section, and claim level; UMAP used
  strictly for exploratory 2D visualisation, never as a semantic-distance
  measurement (`src/embeddings.py`).
- Sentiment/framing analysis is explicitly exploratory: it characterises
  language (positive/negative lexicon, modality, certainty/uncertainty,
  attribution verbs, adversarial framing) and is never used to conclude
  that the document, or its subject, is "biased" (`src/nlp.py`).

## Claim extraction and verification

See schemas in `src/claims.py` / `data/processed/claims.csv` and
`src/validation.py` / `data/processed/claim_evidence.csv` +
`data/processed/claim_assessments.csv`. Verification categories are
non-binary (`supported`, `mostly_supported`, `mixed_or_disputed`,
`misleading_without_context`, `unsupported`, `contradicted`,
`not_independently_verifiable`, `opinion_or_interpretation`) and require
explicit external evidence — no classification is produced from LLM
judgement alone. Source-quality hierarchy is documented in
`src/sources.py` (raw official data > official statistical publications >
legislation/official documents > peer-reviewed research > multilateral
organisations > high-quality independent research > reputable journalism >
commentary > social media), while noting that official status does not
imply correctness — methodological issues in official sources are recorded
too.

## Causality

A standing rule: an indicator moving during a given administration's term
does not, by itself, establish that the administration caused that
movement. Causal language in the source report (`causó`, `provocó`,
`generó`, `debido a`, `como consecuencia de`, `resultado de`, `gracias a`,
`por culpa de`, etc.) is tagged and reviewed separately from descriptive
language (`src/nlp.py`, feeding a dedicated causal-claims review table).

## Cross-data validation

For quantitative claims, priority is given to reconstructing the figure
from original datasets (not just finding another page repeating it),
checking temporal consistency (publication vs. measurement vs. revision
dates), denominators, nominal-vs-real values, per-capita/GDP-share framing,
and known base effects, before comparing to the report's stated figure.
Schema: `data/processed/numeric_claims.csv` (see `src/validation.py`).

## AI authorship / provenance analysis (exploratory)

A dedicated, clearly separated module (`src/authorship.py`,
`notebooks/08_authorship_analysis.ipynb`) evaluates stylometric consistency
across the document using sentence/word-length statistics, type-token
ratio, function-word frequencies, POS distributions, and change-point
detection between segments — always reported as **linguistic patterns**,
never as proof of AI authorship. Any AI-detector output is treated as an
auxiliary, probabilistic signal only, is calibrated first on a
Spanish-language control corpus (human / AI-generated / hybrid) before
being applied to the report, and is reported with its measured
false-positive/false-negative rates alongside the finding — never as a
standalone "X% AI-generated" claim. Strong evidence of AI use would require
independent provenance (metadata, version history, prompt logs, author
acknowledgement) which stylometry and detectors alone cannot supply.

## Reproducibility

Every chart and table must be regenerable via `make <target>` (see
`Makefile`) from versioned inputs. Package versions are pinned in
`requirements.txt`. Every derived dataset is expected to carry a manifest
entry in `outputs/data_manifest.json` recording its source, download date,
hash, and the script that produced it. Methodological decisions —
especially inclusion/exclusion of claims, missing-value handling, period
definitions, and model choices — are logged with rationale in
`RESEARCH_LOG.md`, including negative findings (claims that could not be
verified, models that performed poorly, hypotheses the data did not
support).

## What this document does not yet contain

This is the scaffolding version of the methodology, written before the
source document has been placed in `data/raw/` and before any substantive
NLP or verification work has begun. It will be extended (not replaced) as
concrete methodological choices are made during analysis.
