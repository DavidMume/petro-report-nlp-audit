#!/usr/bin/env python3
"""Score every calibration and report passage with the zero-shot detectors.

Reads  sources/calibration/passages/*.jsonl
Writes outputs/tables/detector_scores.csv   (one row per passage × model pair)

Already-scored passages (same text hash and model pair) are skipped, so the
script can be re-run after adding passages (e.g. the hybrid corpus C) and
only the new ones are scored. Needs torch + transformers and access to
huggingface.co on the first run (the models are cached afterwards).

  --dry-run     tiny random models, no download; writes detector_scores_dryrun.csv
  --size 0.5B   smaller model pair for machines with little memory
  --limit N     score at most N new passages (for a quick test)
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import calibration as cal
from src import detectors as det

META_COLS = ["passage_id", "corpus", "source_id", "generator", "prompt_id", "genre", "period", "chapter",
             "page_start", "page_end", "n_words", "artifact_rate", "text_sha1"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--size", default="1.5B", choices=sorted(det.MODEL_PAIRS))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-tokens", type=int, default=det.MAX_TOKENS)
    a = ap.parse_args()

    import torch
    import transformers

    passages = cal.load_all_passages()
    if passages.empty:
        sys.exit("No passages. Run scripts/build_calibration_corpora.py first.")
    out_path = cal.SCORES_PATH.with_name("detector_scores_dryrun.csv") if a.dry_run else cal.SCORES_PATH

    pair = det.ModelPair.tiny_random() if a.dry_run else det.ModelPair(a.size)
    pair_id = "+".join(pair.names)
    done = pd.read_csv(out_path) if out_path.exists() else pd.DataFrame(columns=["text_sha1", "model_pair"])
    have = set(zip(done.text_sha1, done.model_pair))
    todo = passages[[(h, pair_id) not in have for h in passages.text_sha1]]
    if a.limit:
        todo = todo.head(a.limit)
    print(f"[detectors] {pair_id} on {pair.device}/{str(pair.dtype).replace('torch.', '')}: "
          f"{len(todo)} to score, {len(passages) - len(todo)} already scored")

    rows, t0 = [], time.time()
    env = {"model_pair": pair_id, "device": pair.device, "dtype": str(pair.dtype).replace("torch.", ""),
           "torch_version": torch.__version__, "transformers_version": transformers.__version__,
           "max_tokens": a.max_tokens}

    def save():
        if not rows:
            return
        new = pd.DataFrame(rows)
        allrows = pd.concat([done, new], ignore_index=True) if len(done) else new
        out_path.parent.mkdir(parents=True, exist_ok=True)
        allrows.to_csv(out_path, index=False)

    for i, r in enumerate(todo.itertuples(index=False), 1):
        s = pair.score(r.text, a.max_tokens)
        rows.append({**{c: getattr(r, c, None) for c in META_COLS}, **env,
                     "scored_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **s})
        if i % 10 == 0 or i == len(todo):
            el = time.time() - t0
            print(f"  {i}/{len(todo)}  {el / i:.1f} s/passage  ~{el / i * (len(todo) - i) / 60:.0f} min left", flush=True)
            save()
    save()
    print(f"[detectors] wrote {out_path}")


if __name__ == "__main__":
    main()
