# Corpus B — generated passages (synthetic)

All figures and cases in these texts are **fictional**. They exist only as "AI-generated" controls for
detector calibration and must not be quoted as information about Colombia.

| File | Generator | Model ID reported by the generating session | Passages |
|---|---|---|---|
| `raw_haiku.jsonl` | claude-haiku | claude-haiku-4-5-20251001 | 24 |
| `raw_sonnet.jsonl` | claude-sonnet | claude-sonnet-5-5 | 24 |
| `raw_opus.jsonl` | claude-opus | claude-opus-5-5 | 24 |

- **Prompts:** `prompts.jsonl`, verbatim. There are 24, in four genres that mirror the report's parts:
  - `balance_sectorial` (10);
  - `hallazgo_caso` (6);
  - `carta_presentacion` (3);
  - `principios_cierre` (5).

  Each prompt comes in one of two styles:
  - `libre`: "redacta un fragmento sobre…";
  - `notas`: "a partir de estas notas…", with fictional figures to expand. This is the way an official is most likely to use an assistant.

  Every prompt asks for 300–380 words of continuous prose with no headings or bullets.
- **Generation:** 2026-09-30.
  - Each model answered all 24 prompts in one session.
  - The sessions ran as Cowork subagents, not through the bare API: each one had its own system context, and no temperature was set.
  - The sessions were told not to read the report or any other corpus.
- **Normalisation:** `scripts/build_calibration_corpora.py --generated` strips markdown and applies the same `clean_text` as the PDF passages. The result goes to `passages/B_ai.jsonl`.
- **Limitation:** all three models belong to one family. To add other generators, answer the same `prompts.jsonl` with another model and save the answers as `raw_<model>.jsonl`, using the same fields (`passage_id`, `prompt_id`, `genre`, `generator`, `model_reported`, `generated_at`, `text`). Then re-run `scripts/run_detectors_mac.sh`: only the new passages are scored.
