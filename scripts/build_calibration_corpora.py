#!/usr/bin/env python3
"""Build comparable passages for the detector-calibration experiment (§23.5).

  --target     the report (data/raw/Libro-De-La-Verdad.pdf)  -> passages/target_libro.jsonl
  --human      downloaded control PDFs (A_human/pdf/)       -> passages/A_human.jsonl
  --generated  generated / hybrid raw texts (B_ai/*.jsonl, C_hybrid/*.jsonl)
                                                            -> passages/B_ai.jsonl, passages/C_hybrid.jsonl

The report and the human controls go through the same function
(`calibration.pdf_prose_paragraphs` + `build_passages`), so extraction
artefacts affect both in the same way. Generated text is normalised with
`normalise_generated` (markdown stripped, same `clean_text`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import calibration as cal
from src.config import PROCESSED_DIR, RAW_DIR


def build_target() -> pd.DataFrame:
    pdf = next(RAW_DIR.glob("*.pdf"))
    paras = cal.pdf_prose_paragraphs(pdf)
    corpus_paras = pd.read_csv(PROCESSED_DIR / "paragraphs.csv")
    body = corpus_paras[corpus_paras.block_type.isin(["body", "list_item", "quote"])]
    page_chapter = body.groupby("page").chapter.agg(lambda x: x.value_counts().index[0]).to_dict()
    for p in paras:
        p["chapter"] = page_chapter.get(p["page_start"]) or page_chapter.get(p["page_end"]) or "sin capítulo"
    passages = cal.build_passages(paras, break_key="chapter")
    rows = [{**p, "passage_id": f"T{i + 1:03d}", "corpus": "target_libro", "source_id": "LDV2026",
             "genre": "informe_empalme_2026", "generator": None, "period": "2026"} for i, p in enumerate(passages)]
    return cal.passages_frame(rows)


def build_human() -> pd.DataFrame:
    src = pd.read_csv(cal.HUMAN_SOURCES_CSV, dtype=str)
    dl = pd.read_csv(cal.HUMAN_DOWNLOADS_CSV, dtype=str) if cal.HUMAN_DOWNLOADS_CSV.exists() else pd.DataFrame()
    usable = set(dl[dl.get("usable", "False") == "True"].source_id) if len(dl) else set()
    rows = []
    for r in src.itertuples():
        pdf = cal.HUMAN_PDF_DIR / f"{r.source_id}.pdf"
        if r.source_id not in usable or not pdf.exists():
            print(f"[human] skip {r.source_id}: not downloaded or not usable")
            continue
        passages = cal.build_passages(cal.pdf_prose_paragraphs(pdf))
        chosen = cal.evenly_sample(passages, cal.MAX_PASSAGES_PER_SOURCE)
        print(f"[human] {r.source_id}: {len(passages)} passages, kept {len(chosen)}")
        for j, p in enumerate(chosen):
            rows.append({**p, "passage_id": f"{r.source_id}-{j + 1:02d}", "corpus": "A_human",
                         "source_id": r.source_id, "genre": r.genre, "generator": "human", "period": r.period,
                         "chapter": None})
    return cal.passages_frame(rows)


def build_generated(corpus: str, raw_dir: Path) -> pd.DataFrame:
    rows = []
    for f in sorted(raw_dir.glob("raw_*.jsonl")):
        raw = cal.read_jsonl(f)
        for r in raw.to_dict(orient="records"):
            text = cal.normalise_generated(r["text"])
            if cal.n_words(text) < 120:
                print(f"[{corpus}] drop {r['passage_id']}: {cal.n_words(text)} words")
                continue
            rows.append({"passage_id": r["passage_id"], "corpus": corpus, "source_id": r.get("source_id") or r["generator"],
                         "genre": r.get("genre"), "generator": r["generator"], "prompt_id": r.get("prompt_id"),
                         "period": "generated", "text": text})
    return cal.passages_frame(rows) if rows else pd.DataFrame(columns=cal.PASSAGE_COLUMNS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", action="store_true")
    ap.add_argument("--human", action="store_true")
    ap.add_argument("--generated", action="store_true")
    a = ap.parse_args()
    if not (a.target or a.human or a.generated):
        a.target = a.human = a.generated = True
    if a.target:
        t = build_target()
        cal.write_jsonl(t, cal.PASSAGES_DIR / "target_libro.jsonl")
        print(f"[target] {len(t)} passages; words median {t.n_words.median():.0f}")
        print(t.chapter.value_counts().to_string())
    if a.human:
        h = build_human()
        cal.write_jsonl(h, cal.PASSAGES_DIR / "A_human.jsonl")
        print(f"[human] {len(h)} passages from {h.source_id.nunique() if len(h) else 0} sources")
    if a.generated:
        for corpus, d in (("B_ai", cal.AI_DIR), ("C_hybrid", cal.HYBRID_DIR)):
            g = build_generated(corpus, d)
            cal.write_jsonl(g, cal.PASSAGES_DIR / f"{corpus}.jsonl")
            print(f"[{corpus}] {len(g)} passages; generators: {sorted(g.generator.dropna().unique()) if len(g) else []}")


if __name__ == "__main__":
    main()
