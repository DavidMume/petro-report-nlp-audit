# Detector calibration (methodology §23.5)

> **Result (2026-09-30): no detector passed the gate, so none was applied to the report.** Binoculars AUC 0.67
> (95% CI 0.59–0.75), Fast-DetectGPT 0.63 (0.55–0.71), log-perplexity 0.31 (inverted). Separation depends on the
> generator (0.82–0.83 for two models, 0.35 for the third) and is at chance level for sector balances, the
> report's main genre. Full write-up: `RESEARCH_LOG.md`, 2026-09-30. Charts 27–29 in `outputs/charts/`.

No AI-text detector is applied to the report until it has been calibrated here. This folder holds the
control corpora; the code is in `src/calibration.py` (no model needed) and `src/detectors.py` (torch).

## How to run it

On a machine with internet access (the build environment of this repository cannot reach
huggingface.co or the `.gov.co` hosts):

```bash
bash scripts/run_detectors_mac.sh          # macOS or Linux; SIZE=0.5B for < 12 GB of RAM (automatic)
```

It creates `.venv-detectors`, downloads corpus A, builds the passages, scores them (the Qwen2.5 models,
about 6 GB for the 1.5B pair, are downloaded once) and writes the analysis. The same steps are available
as `make calibration-fetch calibration-corpora detectors detectors-analysis DPYTHON=.venv-detectors/bin/python`.
`make detectors-dryrun` runs the whole chain with tiny random models to check the plumbing (its numbers
mean nothing and are git-ignored).

## Corpora

| Folder | What | Status (2026-09-30) |
|---|---|---|
| `A_human/` | Colombian government reports of the same genres as the report, written **before ChatGPT's public release (2022-11-30)**: 6 documents from 2015–2018 (Informes al Congreso, empalme 2018, informe de gestión) and 10 from 2022 (DNP sector closing balances, 2022 empalme reports). `sources.csv` lists title, publisher, date and the basis for that date, genre, host and URL. | 12 of 16 downloaded on 2026-09-30 (H13–H15: host returned 403; H16: connection reset). `scripts/fetch_calibration_human.py` records SHA-256, size, pages and PDF dates in `downloads.csv`, and excludes any file whose PDF creation date is on or after 2022-11-30. PDFs are not redistributed (`pdf/` is git-ignored). |
| `B_ai/` | 72 generated passages: 24 prompts (`prompts.jsonl`, verbatim) × 3 models. | Done. See `B_ai/README.md`. |
| `C_hybrid/` | Human passages from A rewritten by a model ("mejora la redacción sin cambiar los datos"). | Not built: no detector passed on A vs B, and hybrids are harder to detect, so C could not change the conclusion (RESEARCH_LOG, 2026-09-30). |
| `passages/` | Comparable passages (220–400 words) for every corpus and for the report (`target_libro.jsonl`, 128 passages covering the whole text layer). | Built: A 144 (12 documents × 12), B 72, report 128. |

### Comparability rules

- The report and the human controls go through the **same** extraction (`calibration.pdf_prose_paragraphs`):
  PyMuPDF text layer, running headers/footers removed, body-size lines only, hyphenation re-joined, prose filter,
  no OCR. Generated text is normalised with `normalise_generated` (markdown stripped, same `clean_text`).
- Passages are 220–400 words and never cross a chapter of the report; at most 12 evenly spaced passages per human
  document, so no single document dominates.
- `artifact_rate` (extraction debris) is computed for every passage and its own AUC is reported as a confound
  check: if it separates human from generated text, the detectors could be picking up the PDF, not the writing.

## Detectors

All three come from one open-weight pair sharing a tokenizer, Qwen2.5-1.5B (observer) and
Qwen2.5-1.5B-Instruct (performer), multilingual and Apache-2.0 licensed:

- Binoculars (Hans et al., 2024), reference-implementation form;
- Fast-DetectGPT, analytic form (Bao et al., 2024), observer as sampling and scoring model;
- log-perplexity under the observer (naive baseline).

## Analysis and gate

`scripts/analyse_detector_calibration.py`:

- ROC-AUC with a 95% **cluster** bootstrap (resampling source documents and prompts, since passages from one
  document are not independent);
- threshold at a 5% false-positive rate, with **source-grouped** 5-fold cross-validation: the threshold is set on
  some documents and evaluated on held-out documents and held-out prompts;
- sensitivity by period of the human controls (2015–2018 only, 2022 only), by generator and by genre;
- gate per detector: *calibrated* if the lower bound of the AUC interval is ≥ 0.80, the held-out false-positive rate
  is ≤ 10%, and there are ≥ 30 human passages from ≥ 5 documents and ≥ 30 generated passages from ≥ 3 models;
  *preliminary* if it discriminates but the corpora are short of those sizes; *not informative* otherwise;
- only detectors that pass are applied to the report. The result is a **count** of passages above the threshold,
  per chapter, next to the range expected if every passage were human (binomial, using the confidence interval of
  the false-positive rate). It is never a percentage of the report written by AI.

## Known limitations

- The three generators belong to one model family (Claude). The report's drafters, if they used AI, may have used
  other tools. Passages from other models can be added as `B_ai/raw_<model>.jsonl` with the same prompts.
- The 2022 controls predate ChatGPT but not GPT-3 (2020); the 2015–2018 subset is reported separately.
- Controls are older than the report (2015–2022 vs 2026) and come from a different government, so a detector could
  react to era, editorial house style or topic rather than to generation.
- Short passages (≤ 400 words, ≤ 512 tokens) make every zero-shot detector noisier.
- Several 2022 controls are hosted by a press site or a political party's site (`host_type`); the SHA-256 in
  `downloads.csv` fixes exactly which file was used.
