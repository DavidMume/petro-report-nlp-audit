# Web application (planned)

This folder will hold the independent, data-analysis–oriented interactive
web application described in `documents/methodology.md` and the project
brief — **not** the portfolio site itself (`juan-david-portfolio`), which
will only link to and summarise this project.

## Planned stack

- React + Vite + TypeScript
- Recharts or D3 for charts
- Visual language inspired by `DavidMume/juan-david-portfolio`'s editorial
  design, implemented independently in this repository

## Planned sections

```
/            overview
/document    the source document, provenance, page browser
/nlp         exploratory NLP results
/topics      topic modelling outputs
/entities    entities and co-occurrence/concept networks
/claims      searchable claim database
/verification the fact-checking matrix
/data        downloadable tables and manifest
/methodology full methodology writeup
/sources     evidence ledger / bibliography
```

Selecting a claim must let the reader follow:

```
Claim → Original passage → Page → Report source → External evidence → Assessment → Confidence
```

## Status

Not started. This app is built **after** real NLP, claim-extraction and
verification outputs exist — building it against placeholder data would
risk baking in a UI shaped around assumptions rather than actual results.
See `RESEARCH_LOG.md`.
