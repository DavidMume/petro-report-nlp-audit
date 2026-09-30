#!/usr/bin/env python3
"""Calibration analysis for the zero-shot detectors (methodology §23.5).

Reads  outputs/tables/detector_scores.csv  (from scripts/run_detectors.py)
Writes outputs/tables/detector_calibration_metrics.csv   AUC (cluster bootstrap CI), held-out FPR/TPR, per comparison
       outputs/tables/detector_calibration_status.json   gate result per detector + plain-language statements
       outputs/tables/detector_libro_flags.csv           per report passage, only for detectors that passed the gate
       outputs/tables/detector_libro_summary.csv         counts per chapter next to the expected false positives
       outputs/charts/27_detector_calibration_roc.png
       outputs/charts/28_detector_score_distributions.png

No output of this script is a percentage of the report written by AI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import calibration as cal
from src.config import CHARTS_DIR, TABLES_DIR

CORPUS_LABELS = {"A_human": "Humanos (control, 2015–2022)", "B_ai": "Generados por IA (control)",
                 "C_hybrid": "Híbridos (control)", "target_libro": "El Libro de la Verdad"}


def charts(scores: pd.DataFrame, gate: dict, suffix: str = "") -> None:
    import matplotlib.pyplot as plt

    from src import visualisations as vz
    vz.setup_style()
    s = cal.oriented_scores(scores)
    dets = [d for d in cal.DETECTORS if f"ai_score__{d}" in s]
    note = "Fuente: corpus de control A/B/C y El Libro de la Verdad (2026); cálculos propios — petro-report-nlp-audit"

    # ROC curves, primary comparison (A vs B)
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    A, B = s[s.corpus == "A_human"], s[s.corpus == "B_ai"]
    for k, d in enumerate(dets):
        col = f"ai_score__{d}"
        y = np.r_[np.zeros(len(A)), np.ones(len(B))]
        sc = np.r_[A[col].to_numpy(float), B[col].to_numpy(float)]
        thr = np.unique(sc)[::-1]
        tpr = [((sc >= t) & (y == 1)).sum() / max((y == 1).sum(), 1) for t in thr]
        fpr = [((sc >= t) & (y == 0)).sum() / max((y == 0).sum(), 1) for t in thr]
        auc = cal.auc(y, sc)
        ax.plot([0] + fpr, [0] + tpr, color=vz.CATEGORICAL[k], lw=1.8,
                label=f"{cal.DETECTORS[d]['label']} · AUC {auc:.2f} · {gate.get(d, {}).get('status', '')}")
    ax.plot([0, 1], [0, 1], color=vz.DEEMPH, lw=1, ls="--")
    ax.axvline(cal.GATE["target_fpr"], color=vz.MUTED, lw=0.8)
    ax.set_xlabel("Tasa de falsos positivos (textos humanos marcados)")
    ax.set_ylabel("Tasa de detección (textos generados marcados)")
    ax.set_title("Calibración de detectores: humanos vs generados")
    ax.legend(loc="lower right", fontsize=7)
    ax.set_xlim(0, 1), ax.set_ylim(0, 1.01)
    vz._finish(fig, ax, CHARTS_DIR / f"27_detector_calibration_roc{suffix}.png",
               subtitle="Curvas ROC sobre el corpus de control. La línea vertical marca la tasa de falsos positivos "
                        "objetivo (5%). Un detector sin capacidad de separar sigue la diagonal.", note=note)

    # Score distributions by corpus, one panel per detector
    fig, axes = plt.subplots(len(dets), 1, figsize=(7.2, 2.2 * len(dets) + 0.6), squeeze=False)
    order = [c for c in CORPUS_LABELS if c in set(s.corpus)]
    for ax, d in zip(axes[:, 0], dets):
        col = f"ai_score__{d}"
        data = [s[s.corpus == c][col].dropna().to_numpy(float) for c in order]
        style = dict(widths=0.55, patch_artist=True, showfliers=True,
                     boxprops={"facecolor": vz.SEQ_BLUE[1], "edgecolor": vz.AXIS},
                     medianprops={"color": vz.INK}, whiskerprops={"color": vz.AXIS}, capprops={"color": vz.AXIS},
                     flierprops={"marker": "o", "markersize": 2.5, "markerfacecolor": vz.MUTED,
                                 "markeredgecolor": "none"})
        try:
            ax.boxplot(data, orientation="horizontal", **style)
        except TypeError:  # matplotlib < 3.10
            ax.boxplot(data, vert=False, **style)
        ax.set_yticks(range(1, len(order) + 1), [CORPUS_LABELS[c] for c in order])
        g = gate.get(d, {})
        if "threshold" in g:
            ax.axvline(g["threshold"], color=vz.CATEGORICAL[1], lw=1)
        ax.set_title(f"{cal.DETECTORS[d]['label']} — {g.get('status', '')}", fontsize=9.5)
        ax.xaxis.grid(True)
        ax.set_axisbelow(True)
        ax.invert_yaxis()
    axes[-1, 0].set_xlabel("Puntaje orientado (más a la derecha = más parecido a los textos generados)")
    vz._finish(fig, None, CHARTS_DIR / f"28_detector_score_distributions{suffix}.png",
               subtitle="La línea naranja es el umbral que el 95% de los textos humanos de control no supera. "
                        "Un pasaje a la derecha del umbral no está probado como escrito por IA.", note=note)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="analyse detector_scores_dryrun.csv (meaningless scores)")
    ap.add_argument("--model-pair", default=None)
    a = ap.parse_args()
    path = cal.SCORES_PATH.with_name("detector_scores_dryrun.csv") if a.dry_run else cal.SCORES_PATH
    if not path.exists():
        sys.exit(f"{path} not found. Run scripts/run_detectors.py first.")
    scores = pd.read_csv(path)
    pair = a.model_pair or scores.model_pair.value_counts().index[0]
    scores = scores[scores.model_pair == pair]
    counts0 = scores.corpus.value_counts()
    if counts0.get("A_human", 0) < 5 or counts0.get("B_ai", 0) < 5:
        sys.exit(f"Not enough scored control passages ({counts0.to_dict()}). Run fetch/build/run_detectors first.")
    res = cal.run_analysis(scores)
    suffix = "_dryrun" if a.dry_run else ""

    res.metrics.round(4).to_csv(TABLES_DIR / f"detector_calibration_metrics{suffix}.csv", index=False)
    res.flags.to_csv(TABLES_DIR / f"detector_libro_flags{suffix}.csv", index=False)
    res.summary.to_csv(TABLES_DIR / f"detector_libro_summary{suffix}.csv", index=False)
    counts = scores.corpus.value_counts().to_dict()
    status = {
        "status": "calibration_run" + ("_dryrun" if a.dry_run else ""),
        "model_pair": pair,
        "passages": counts,
        "passages_dropped_nonfinite_or_short": int(len(scores) - len(cal.oriented_scores(scores))),
        "human_sources": int(scores[scores.corpus == "A_human"].source_id.nunique()),
        "generators": sorted(scores[scores.corpus == "B_ai"].generator.dropna().unique().tolist()),
        "gate_rule": cal.GATE,
        "detectors": res.gate,
        "statements_es": res.statements,
        "reason": ("Detectores de ceros disparos calibrados sobre textos de control en español. Un detector solo se "
                   "aplica al informe si pasa la compuerta; sus marcas se informan como conteos junto al número "
                   "esperado de falsos positivos, nunca como porcentaje del documento escrito por IA."),
    }
    if a.dry_run:
        status["warning"] = "DRY RUN with tiny random models: the numbers are meaningless."
    payload = json.dumps(status, indent=2, ensure_ascii=False) + "\n"
    (TABLES_DIR / f"detector_calibration_status{suffix}.json").write_text(payload)
    if not a.dry_run:  # the file the web app and run_authorship.py read
        (TABLES_DIR / "ai_detector_status.json").write_text(payload)
    charts(scores, res.gate, suffix)

    prim = res.metrics[res.metrics.comparison.str.startswith(("primary", "confound"))]
    print(prim[["detector", "comparison", "n_human", "n_ai", "roc_auc", "auc_ci_low", "auc_ci_high",
                "cv_fpr", "cv_tpr"]].round(3).to_string(index=False))
    for d, g in res.gate.items():
        print(f"  {d}: {g['status']}  {'; '.join(g.get('reasons', []))}")
    for line in res.statements:
        print("-", line)


if __name__ == "__main__":
    main()
