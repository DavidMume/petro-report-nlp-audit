# petro-report-nlp-audit

Reproducible NLP, data analysis and claim-verification audit of a published
report about a Colombian presidential administration.

> **Status: scaffolding stage.** No source document has been formally
> ingested yet, and no substantive NLP, entity, topic, or claim-verification
> results exist. This repository currently contains project structure,
> schemas, stub modules, and an initial test suite only. See
> `RESEARCH_LOG.md` for what has and hasn't been done and why.

## Research question

This project does not start from, and does not produce, a verdict on
whether the report is "true," "false," or favourable/unfavourable to any
government or political figure. It separates three distinct questions:

1. **What does the report claim?** (descriptive extraction)
2. **How does it construct its argument?** (structure, framing, language)
3. **How well do its verifiable claims hold up against external evidence?**
   (claim-by-claim verification, non-binary outcomes)

> ¿Qué afirma el informe, cómo construye esas afirmaciones y qué tan bien se
> sostienen cuando se contrastan sistemáticamente con evidencia externa?

Seven research questions (RQ1–RQ7) guide the work; RQ7 (linguistic
provenance / possible AI assistance in drafting) is explicitly exploratory
and is never framed as "what percentage was AI-written." Full methodology,
including the causality rule, the source-quality hierarchy, and the
AI-authorship-analysis guardrails, is in `documents/methodology.md`.

## Source document

Not yet confirmed/ingested. `data/raw/` is empty and
`documents/source_metadata.json` is a null-valued placeholder by design —
this project does not assume a title, publisher, or organisation name
(including any acronym) before verifying it directly against the source
PDF. See `data/raw/README.md` for the ingestion procedure and immutability
rule, and `RESEARCH_LOG.md` for the current status of a candidate document.

## Methodology (summary)

- **Provenance first.** Every source file is hashed (SHA-256), dated, and
  recorded before analysis; `data/raw/` is treated as immutable.
- **Traceability.** Every corpus row and every claim traces back to a
  specific page/section of the original document.
- **NLP is descriptive, not adjudicative.** Frequency, TF-IDF, NER, topic
  modelling, embeddings, and sentiment/framing analysis characterise the
  text; none of them are used to declare the document biased or accurate.
- **Claims are verified against explicit external evidence**, never
  classified from model judgement alone, using eight non-binary outcome
  categories (`supported` → `opinion_or_interpretation`; see
  `src/config.py::VERIFICATION_STATUSES`).
- **Causality is treated carefully.** An indicator moving during an
  administration's term does not by itself establish that the
  administration caused the movement; causal language in the source is
  tagged and reviewed separately from descriptive language.
- **AI-authorship analysis is exploratory and evidence-gated.** Stylometry
  and AI detectors are calibrated on a Spanish-language control corpus
  before ever being applied to the report, and are reported as
  probabilistic linguistic patterns — never as a definitive "X% AI-written"
  claim. Full detail in `documents/methodology.md` §23 and `src/authorship.py`.
- **Reproducibility.** Every table and chart regenerates via `make <target>`
  from pinned dependencies; methodological decisions (including negative
  findings) are logged in `RESEARCH_LOG.md`.

Full methodology: [`documents/methodology.md`](documents/methodology.md).

## Project structure

```
petro-report-nlp-audit/
├── data/               raw (immutable) / interim / processed / external data
├── documents/          source provenance metadata + full methodology
├── notebooks/          01-08, exploratory notebooks mirroring the pipeline
├── src/                pipeline modules (extraction, NLP, claims, validation, …)
├── scripts/            CLI entry points wired to `make` targets
├── outputs/            tables, charts, network exports, data manifest
├── sources/            source registry + evidence ledger
├── web/                planned interactive React/Vite data app
└── tests/              pytest suite
```

## Reproducibility / installation

```bash
git clone https://github.com/DavidMume/petro-report-nlp-audit.git
cd petro-report-nlp-audit
make install          # creates .venv and installs pinned dependencies
python -m spacy download es_core_news_lg   # Spanish NLP model (not on PyPI by name)
```

## Usage (pipeline, once the source document is confirmed)

```bash
# 1. Place the confirmed, original PDF in data/raw/ and fill in
#    documents/source_metadata.json's known fields (title, publisher, etc.)
make extract      # PDF -> page-level text (PyMuPDF -> pdfplumber -> OCR)
make corpus       # -> data/processed/corpus.{parquet,csv}
make nlp          # frequencies, TF-IDF, NER, topics, embeddings
make claims       # candidate claim extraction (requires human review before use)
make validation   # evidence gathering + assessment against sources/evidence_ledger.csv
make charts       # regenerate outputs/charts and outputs/networks
make test         # run the test suite
```

Each stage is a script in `scripts/` calling into `src/`; see
`documents/methodology.md` for what each stage does and does not claim.

## Data provenance

- `documents/source_metadata.json` — title, publisher, authors, dates, URL,
  filename, SHA-256, page count for the source document.
- `outputs/data_manifest.json` — filename, source, download date, hash,
  row/column counts, and producing script for every derived dataset.
- `sources/evidence_ledger.csv` — every external source consulted during
  claim verification, with URL, type, access date, and which claims it
  bears on.
- `RESEARCH_LOG.md` — dated methodological decisions and their rationale,
  including negative findings.

## Caveats and limitations

- This is a single-document audit; findings describe this report, not a
  general assessment of any administration's performance.
- NLP outputs (topics, sentiment/framing, embeddings) are exploratory and
  descriptive; they characterise language use, not truth or bias.
- Claim verification depends on the availability and quality of public,
  citable evidence; "not independently verifiable" is a valid, expected
  outcome for some claims, not a failure of the method.
- AI-authorship signals (RQ6/RQ7) are probabilistic and calibrated on a
  necessarily limited control corpus; they cannot establish direct AI
  authorship without independent provenance evidence (see
  `documents/methodology.md` §33).
- The web application (`web/`) does not exist yet; it is built only once
  real pipeline outputs exist, to avoid designing an interface around
  placeholder data.

## Outputs

Once the pipeline has run: tables in `outputs/tables/`, charts in
`outputs/charts/`, network exports (`.graphml`) in `outputs/networks/`, and
assembled reports in `outputs/reports/`. Chart inventory is defined in
`src/visualisations.py::CHART_REGISTRY` and documented in
`documents/methodology.md` §15.

## Website

Planned integration:

- A standalone interactive data app in `web/` (React + Vite + TypeScript),
  independent of the portfolio site, letting readers trace
  Claim → Original passage → Page → Report source → External evidence →
  Assessment → Confidence.
- A project page and an independent editorial article added later to
  [`DavidMume/juan-david-portfolio`](https://github.com/DavidMume/juan-david-portfolio)
  (published at [juandamunoz.com](https://juandamunoz.com)), on a feature
  branch (`feature/petro-report-nlp-audit`), never committed directly to
  `main`. See `documents/methodology.md` §17-18 for the required content
  and cross-linking rules, and that repo's `ARTICLE_INTEGRATION_HANDBOOK.md`
  before writing the article.

## Repository status

- **Local repo:** initialised, `main` branch, first commit made (see git
  log).
- **GitHub remote:** not yet created. `gh auth status` reported no valid
  GitHub authentication in this environment (`GH_TOKEN` was present but
  invalid). To publish once authenticated as `DavidMume`:

  ```bash
  gh auth login
  gh repo create DavidMume/petro-report-nlp-audit \
    --public \
    --source=. \
    --remote=origin \
    --description "Reproducible NLP, data analysis and claim verification of a political report about Colombia."
  git push -u origin main
  ```

## Citation

If referencing this work before a formal citation format is established,
cite as:

> Mume, J.D. (2026). *petro-report-nlp-audit*: Reproducible NLP, data
> analysis and claim-verification audit of a political report about
> Colombia. https://github.com/DavidMume/petro-report-nlp-audit

## License

Code is MIT-licensed (see `LICENSE`). The source PDF under audit is used
for research, criticism and commentary under its own rights holder's terms
and is not relicensed by this repository.
