# Detector calibration corpora (methodology §23.5) — not yet assembled

No AI-text detector may be applied to the report until this experiment has
been run and its metrics logged in `RESEARCH_LOG.md`.

## Layout (to create)

```
sources/calibration/
  A_human/        Spanish public-policy / economic / institutional texts about Colombia, 2015-2021
                  (pre-LLM). One .txt per document + metadata.csv (source, url, date, sha256).
  B_ai/           Generated texts. metadata.csv: model, model_version, prompt, temperature, date.
                  Prompts stored verbatim in prompts/.
  C_hybrid/       ai_then_human_edited/, human_then_ai_rewritten/, ai_paraphrased/ (+ metadata.csv)
```

## Rules

- Match genre and length to the report's segments (~700 words; institutional Spanish).
- At least 3 generating models for B; at least 30 segments per corpus.
- Run each detector over A/B/C with `src.authorship.run_detector_calibration_experiment` and record precision, recall, specificity, false-positive rate, false-negative rate, F1 and ROC-AUC.
- A detector validated only in English is excluded from the primary analysis or labelled "exploratory only".
- Report detector results as counts ("the detector flagged X of 61 segments") next to its false-positive rate, never as a percentage of the document written by AI.
