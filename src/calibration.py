"""AI-text detector calibration (methodology §23.5). EXPLORATORY.

This module holds everything that does not need a language model:

- building comparable prose passages from PDFs (the report and the human
  control documents go through the *same* extraction path);
- normalising generated text so that formatting cannot give the game away;
- the calibration analysis: ROC-AUC with a cluster bootstrap, thresholds set
  at a target false-positive rate with source-grouped cross-validation, the
  gate that decides whether a detector may be applied at all, and the
  application to the report reported as counts next to the expected number of
  false positives.

Scoring with language models lives in `src/detectors.py` (needs torch).

What this module never does: state what share of the report was written by
AI. Allowed phrasing is listed in `src/authorship.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import SOURCES_DIR, TABLES_DIR
from src.preprocess import clean_text, collapse_whitespace, join_lines, normalise_unicode

CALIBRATION_DIR = SOURCES_DIR / "calibration"
HUMAN_DIR = CALIBRATION_DIR / "A_human"
HUMAN_SOURCES_CSV = HUMAN_DIR / "sources.csv"
HUMAN_PDF_DIR = HUMAN_DIR / "pdf"  # not committed (see .gitignore); hashes are
HUMAN_DOWNLOADS_CSV = HUMAN_DIR / "downloads.csv"
AI_DIR = CALIBRATION_DIR / "B_ai"
HYBRID_DIR = CALIBRATION_DIR / "C_hybrid"
PASSAGES_DIR = CALIBRATION_DIR / "passages"
SCORES_PATH = TABLES_DIR / "detector_scores.csv"

CHATGPT_RELEASE = "2022-11-30"  # public release of ChatGPT; human controls must predate it
MIN_WORDS, MAX_WORDS = 220, 400
MAX_PASSAGES_PER_SOURCE = 12
SEED = 20260930

PASSAGE_COLUMNS = ["passage_id", "corpus", "source_id", "genre", "generator", "prompt_id", "period",
                   "page_start", "page_end", "chapter", "n_words", "artifact_rate", "text_sha1", "text"]

# Detector scores are oriented so that HIGHER = more similar to the AI-generated controls.
# (Binoculars: lower raw score = more machine-like, so its sign is flipped.)
DETECTORS = {
    "binoculars": {"raw": "binoculars", "sign": -1.0, "label": "Binoculars (Qwen2.5 base/instruct)"},
    "fast_detectgpt": {"raw": "fast_detectgpt", "sign": 1.0, "label": "Fast-DetectGPT analítico (Qwen2.5 base)"},
    "log_perplexity": {"raw": "logppl_observer", "sign": -1.0, "label": "Log-perplejidad (línea base)"},
}

# Gate (§23.5): a detector is applied to the report only if all of these hold.
GATE = {"min_auc_ci_low": 0.80, "max_cv_fpr": 0.10, "min_human": 30, "min_ai": 30,
        "min_human_sources": 5, "min_generators": 3, "target_fpr": 0.05}


# --- Text helpers ---------------------------------------------------------------------------

_SENT_SPLIT = re.compile(r"(?<=[.;:!?])\s+(?=[«“\"(¿¡]?[A-ZÁÉÍÓÚÑ0-9])")
_WORD = re.compile(r"\w+", re.UNICODE)
_ODD_TOKEN = re.compile(r"^(?:[b-df-hj-np-tv-xzB-DF-HJ-NP-TV-XZ]|\w*\d+[a-zA-Z]+\d*\w*|[a-zA-Z]+\d+\w*)$")


def text_sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def n_words(text: str) -> int:
    return len(_WORD.findall(text))


def split_sentences(text: str) -> list[str]:
    return [s for s in _SENT_SPLIT.split(text) if s.strip()]


def artifact_rate(text: str) -> float:
    """Share of whitespace tokens that look like extraction debris (stray single
    consonants, letter-digit fusions). Used to check that the detectors are not
    simply separating 'extracted from a PDF' from 'typed into a chat'."""
    toks = [t.strip(".,;:()«»“”\"'¿?¡!") for t in text.split()]
    toks = [t for t in toks if t]
    if not toks:
        return 0.0
    return sum(bool(_ODD_TOKEN.match(t)) for t in toks) / len(toks)


def normalise_generated(text: str) -> str:
    """Strip chat formatting from generated text (markdown headings, bold,
    bullets, numbered lists, surrounding quotes) and apply the same
    `clean_text` normalisation as the PDF-derived passages."""
    t = normalise_unicode(text)
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)
    t = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), t)
    t = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", t)
    t = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", t, flags=re.M)
    t = collapse_whitespace(t).strip("\"“”«» ")
    return clean_text(t)


# --- Passages from PDFs ---------------------------------------------------------------------

def _is_prose(text: str) -> bool:
    words = _WORD.findall(text)
    if len(words) < 20:
        return False
    digits = sum(w.isdigit() for w in words) / len(words)
    upper = sum(c.isupper() for c in text) / max(sum(c.isalpha() for c in text), 1)
    alpha = sum(c.isalpha() or c.isspace() for c in text) / max(len(text), 1)
    return digits <= 0.20 and upper <= 0.30 and alpha >= 0.80


def pdf_prose_paragraphs(pdf_path: Path, top_frac: float = 0.09, bottom_frac: float = 0.93,
                         min_repetitions: int = 3, size_tol: float = 1.0) -> list[dict]:
    """Prose paragraphs from a PDF text layer with PyMuPDF.

    1. Running headers/footers: lines in the top/bottom margin that repeat on
       >= `min_repetitions` pages are dropped.
    2. Body text: only lines whose font size is within `size_tol` pt of the
       document's dominant (character-weighted) size are kept, so titles,
       headings, footnotes and most figure labels are left out.
    3. Lines are joined in reading order (hyphenation re-joined); a paragraph
       ends at a block boundary when its text ends in terminal punctuation,
       and otherwise continues into the next block or page.
    4. Paragraphs that fail the prose filter (tables, lists of figures) are
       dropped. Image-only pages yield nothing (no OCR — the same rule is
       applied to the report and to the controls)."""
    from collections import Counter, defaultdict

    from src.extract import extract_with_pymupdf

    pages = extract_with_pymupdf(Path(pdf_path))

    def margin(ln, p):
        return ln.bbox[1] < top_frac * p.height or ln.bbox[1] > bottom_frac * p.height

    def key(t):
        return re.sub(r"\d+", "#", collapse_whitespace(t)).upper()

    seen: dict[str, set[int]] = defaultdict(set)
    sizes: Counter = Counter()
    for p in pages:
        for b in p.blocks:
            for ln in b.lines:
                if margin(ln, p):
                    seen[key(ln.text)].add(p.page_number)
                sizes[ln.size] += len(ln.text)
    repeated = {k for k, v in seen.items() if len(v) >= min_repetitions}
    if not sizes:
        return []
    body_size = sizes.most_common(1)[0][0]

    paras: list[dict] = []
    cur: dict | None = None

    def close():
        nonlocal cur
        if cur is not None:
            cur["text"] = clean_text(join_lines(cur.pop("lines"))[0])
            paras.append(cur)
        cur = None

    for p in pages:
        for b in p.blocks:
            lines = [ln.text for ln in b.lines
                     if abs(ln.size - body_size) <= size_tol and not (margin(ln, p) and key(ln.text) in repeated)]
            if not lines:
                continue
            if cur is None:
                cur = {"page_start": p.page_number, "page_end": p.page_number, "lines": []}
            cur["lines"].extend(lines)
            cur["page_end"] = p.page_number
            if re.search(r"[.!?»”)]\s*$", lines[-1]):
                close()
    close()
    return [q for q in paras if _is_prose(q["text"])]


def build_passages(paragraphs: list[dict], min_words: int = MIN_WORDS, max_words: int = MAX_WORDS,
                   break_key: str | None = None) -> list[dict]:
    """Group consecutive paragraphs into passages of `min_words`–`max_words`
    words. Paragraphs longer than `max_words` are split at sentence
    boundaries. A passage never crosses a change in `break_key` (e.g. the
    report's chapter). Leftovers shorter than `min_words` are dropped."""
    units: list[dict] = []
    for p in paragraphs:
        if n_words(p["text"]) <= max_words:
            units.append(p)
            continue
        chunk: list[str] = []
        for s in split_sentences(p["text"]):
            if chunk and n_words(" ".join(chunk + [s])) > max_words:
                units.append({**p, "text": " ".join(chunk)})
                chunk = []
            chunk.append(s)
        if chunk:
            units.append({**p, "text": " ".join(chunk)})

    out: list[dict] = []
    cur: list[dict] = []

    def flush():
        if cur and n_words(" ".join(u["text"] for u in cur)) >= min_words:
            out.append({**{k: v for k, v in cur[0].items() if k not in ("text", "page_end")},
                        "page_start": cur[0]["page_start"], "page_end": cur[-1]["page_end"],
                        "text": " ".join(u["text"] for u in cur)})
        cur.clear()

    for u in units:
        if cur and break_key and u.get(break_key) != cur[-1].get(break_key):
            flush()
        if cur and n_words(" ".join(x["text"] for x in cur + [u])) > max_words:
            flush()
        cur.append(u)
    flush()
    return out


def evenly_sample(items: list, k: int) -> list:
    """Deterministic, evenly spaced sample across a document (no RNG, so it
    does not depend on library versions)."""
    if len(items) <= k:
        return list(items)
    idx = np.linspace(0, len(items) - 1, k).round().astype(int)
    return [items[i] for i in sorted(set(idx))]


def passages_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for c in PASSAGE_COLUMNS:
        if c not in df:
            df[c] = None
    df["n_words"] = df.text.map(n_words)
    df["artifact_rate"] = df.text.map(artifact_rate).round(4)
    df["text_sha1"] = df.text.map(text_sha1)
    return df[PASSAGE_COLUMNS]


def write_jsonl(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in df.to_dict(orient="records"):
            f.write(json.dumps(rec, ensure_ascii=False, default=lambda o: None if pd.isna(o) else o) + "\n")


def read_jsonl(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame(columns=PASSAGE_COLUMNS)
    with open(path, encoding="utf-8") as f:
        return pd.DataFrame([json.loads(line) for line in f if line.strip()])


def load_all_passages() -> pd.DataFrame:
    frames = [read_jsonl(p) for p in sorted(PASSAGES_DIR.glob("*.jsonl"))]
    frames = [f for f in frames if len(f)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=PASSAGE_COLUMNS)


# --- Calibration analysis -------------------------------------------------------------------

def oriented_scores(scores: pd.DataFrame) -> pd.DataFrame:
    """Add one `ai_score__<detector>` column per detector (higher = more AI-like).
    Rows with non-finite scores or too few tokens are dropped (they are counted
    in the status file by the analysis script)."""
    out = scores.copy()
    if "nonfinite" in out:
        out = out[~out.nonfinite.fillna(False).astype(bool)]
    if "binoculars" in out:
        out = out[np.isfinite(out.binoculars.astype(float))]
    for name, d in DETECTORS.items():
        if d["raw"] in out:
            out[f"ai_score__{name}"] = d["sign"] * out[d["raw"]].astype(float)
    return out


def auc(y: np.ndarray, s: np.ndarray) -> float:
    """ROC-AUC via the Mann–Whitney statistic (ties count one half)."""
    y = np.asarray(y).astype(int)
    s = np.asarray(s, dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    from scipy.stats import rankdata
    ranks = rankdata(np.concatenate([neg, pos]))  # average ranks for ties
    rank_pos = ranks[len(neg):].sum()
    return float((rank_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def cluster_bootstrap_auc(y, s, groups, n_boot: int = 2000, seed: int = SEED) -> tuple[float, float]:
    """95% interval for ROC-AUC resampling whole clusters (source documents
    for human text, prompts for generated text), because passages from the
    same document are not independent."""
    rng = np.random.default_rng(seed)
    y, s, groups = np.asarray(y), np.asarray(s, dtype=float), np.asarray(groups)
    g0 = [np.flatnonzero((groups == g) & (y == 0)) for g in pd.unique(groups[y == 0])]
    g1 = [np.flatnonzero((groups == g) & (y == 1)) for g in pd.unique(groups[y == 1])]
    vals = []
    for _ in range(n_boot):
        i0 = np.concatenate([g0[k] for k in rng.integers(0, len(g0), len(g0))])
        i1 = np.concatenate([g1[k] for k in rng.integers(0, len(g1), len(g1))])
        idx = np.concatenate([i0, i1])
        vals.append(auc(y[idx], s[idx]))
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def _folds(groups: np.ndarray, n_splits: int) -> list[np.ndarray]:
    uniq = sorted(pd.unique(groups))
    return [np.isin(groups, uniq[k::n_splits]) for k in range(min(n_splits, len(uniq)))]


def grouped_cv_threshold(h_scores, h_groups, a_scores, a_groups, target_fpr: float = GATE["target_fpr"],
                         n_splits: int = 5) -> dict:
    """Threshold = (1 - target_fpr) quantile of human scores in the training
    folds; FPR and TPR are measured on held-out *source documents* (human) and
    held-out *prompts* (generated). Returns pooled held-out rates and the final
    threshold fitted on all human passages."""
    h_scores, a_scores = np.asarray(h_scores, float), np.asarray(a_scores, float)
    h_groups, a_groups = np.asarray(h_groups), np.asarray(a_groups)
    hf, af = _folds(h_groups, n_splits), _folds(a_groups, n_splits)
    fp = tn = tp = fn = 0
    for k in range(min(len(hf), len(af))):
        thr = np.quantile(h_scores[~hf[k]], 1 - target_fpr)
        fp += int((h_scores[hf[k]] > thr).sum())
        tn += int((h_scores[hf[k]] <= thr).sum())
        tp += int((a_scores[af[k]] > thr).sum())
        fn += int((a_scores[af[k]] <= thr).sum())
    return {"threshold": float(np.quantile(h_scores, 1 - target_fpr)),
            "cv_fpr": fp / max(fp + tn, 1), "cv_tpr": tp / max(tp + fn, 1),
            "cv_fp": fp, "cv_tn": tn, "cv_tp": tp, "cv_fn": fn}


def calibrate(scores: pd.DataFrame) -> pd.DataFrame:
    """One row per (detector, comparison). Comparisons:
    - primary: all human (A) vs all generated (B);
    - by period of the human controls (2015-2018 only / 2022 only);
    - by generator and by genre of the generated text;
    - hybrid (C) vs human, when C exists;
    - `artifact_rate` alone, as a confound check."""
    s = oriented_scores(scores)
    A = s[s.corpus == "A_human"]
    B = s[s.corpus == "B_ai"]
    C = s[s.corpus == "C_hybrid"]
    rows = []

    def add(det, comp, h, a, score_col, extra=None):
        if len(h) < 5 or len(a) < 5:
            return
        y = np.r_[np.zeros(len(h)), np.ones(len(a))]
        sc = np.r_[h[score_col].to_numpy(float), a[score_col].to_numpy(float)]
        grp = np.r_[h.source_id.astype(str).to_numpy(), a.prompt_id.fillna(a.passage_id).astype(str).to_numpy()]
        lo, hi = cluster_bootstrap_auc(y, sc, grp)
        cv = grouped_cv_threshold(h[score_col], h.source_id.astype(str), a[score_col],
                                  a.prompt_id.fillna(a.passage_id).astype(str))
        rows.append({"detector": det, "comparison": comp, "n_human": len(h), "n_ai": len(a),
                     "n_human_sources": h.source_id.nunique(), "n_generators": a.generator.nunique(),
                     "roc_auc": auc(y, sc), "auc_ci_low": lo, "auc_ci_high": hi, **cv, **(extra or {})})

    for det in DETECTORS:
        col = f"ai_score__{det}"
        if col not in s:
            continue
        add(det, "primary: A vs B", A, B, col)
        for per in sorted(A.period.dropna().unique()):
            add(det, f"A[{per}] vs B", A[A.period == per], B, col)
        for gen in sorted(B.generator.dropna().unique()):
            add(det, f"A vs B[{gen}]", A, B[B.generator == gen], col)
        for gen in sorted(B.genre.dropna().unique()):
            add(det, f"A vs B[genre={gen}]", A, B[B.genre == gen], col)
        if len(C):
            add(det, "A vs C (hybrid)", A, C, col)
    add("artifact_rate", "confound: A vs B", A.assign(x=-A.artifact_rate), B.assign(x=-B.artifact_rate), "x")
    return pd.DataFrame(rows)


def gate(metrics: pd.DataFrame) -> dict:
    """Decide, per detector, whether it may be applied to the report.
    'calibrated'   — every GATE condition holds;
    'preliminary'  — discriminates well but the corpora are below the size /
                     diversity requirements (e.g. fewer than 3 generators);
    'not_informative' — fails the discrimination or false-positive condition."""
    out = {}
    if metrics.empty or "comparison" not in metrics:
        return {det: {"status": "not_run", "reasons": ["faltan pasajes humanos o generados con puntaje"]}
                for det in DETECTORS}
    prim = metrics[metrics.comparison == "primary: A vs B"].set_index("detector")
    for det in DETECTORS:
        if det not in prim.index:
            out[det] = {"status": "not_run", "reasons": ["sin puntajes"]}
            continue
        m = prim.loc[det]
        reasons = []
        if m.auc_ci_low < GATE["min_auc_ci_low"]:
            reasons.append(f"límite inferior del IC 95% del AUC {m.auc_ci_low:.2f} < {GATE['min_auc_ci_low']}")
        if m.cv_fpr > GATE["max_cv_fpr"]:
            reasons.append(f"tasa de falsos positivos en validación {m.cv_fpr:.2f} > {GATE['max_cv_fpr']}")
        size = []
        if m.n_human < GATE["min_human"]:
            size.append(f"solo {m.n_human} pasajes humanos")
        if m.n_ai < GATE["min_ai"]:
            size.append(f"solo {m.n_ai} pasajes generados")
        if m.n_human_sources < GATE["min_human_sources"]:
            size.append(f"solo {m.n_human_sources} documentos humanos de origen")
        if m.n_generators < GATE["min_generators"]:
            size.append(f"solo {m.n_generators} modelos generadores")
        status = "not_informative" if reasons else ("preliminary" if size else "calibrated")
        out[det] = {"status": status, "reasons": reasons + size, "threshold": float(m.threshold),
                    "cv_fpr": float(m.cv_fpr), "cv_fpr_ci": list(fpr_interval(int(m.cv_fp), int(m.cv_fp + m.cv_tn))),
                    "cv_tpr": float(m.cv_tpr), "roc_auc": float(m.roc_auc),
                    "auc_ci": [float(m.auc_ci_low), float(m.auc_ci_high)]}
    return out


def fpr_interval(fp: int, n_human: int) -> tuple[float, float]:
    """Clopper–Pearson 95% interval for the held-out false-positive rate."""
    from scipy.stats import beta
    lo = 0.0 if fp == 0 else float(beta.ppf(0.025, fp, n_human - fp + 1))
    hi = 1.0 if fp == n_human else float(beta.ppf(0.975, fp + 1, n_human - fp))
    return lo, hi


def expected_false_positive_interval(n: int, fpr_low: float, fpr_high: float | None = None) -> tuple[int, int]:
    """Range of the number of passages a detector would flag among `n`
    *human-written* passages. Uses the 2.5% binomial quantile at the lower
    end of the false-positive-rate interval and the 97.5% quantile at its
    upper end, so the uncertainty of the threshold itself is included."""
    from scipy.stats import binom
    fpr_high = fpr_low if fpr_high is None else fpr_high
    return int(binom.ppf(0.025, n, fpr_low)), int(binom.ppf(0.975, n, fpr_high))


def apply_to_target(scores: pd.DataFrame, gate_result: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Flags per report passage and a summary per detector × chapter, only for
    detectors whose gate status is 'calibrated' or 'preliminary'. A flag means
    'score above the threshold that 95% of the human controls stay below' —
    nothing more."""
    s = oriented_scores(scores)
    T = s[s.corpus == "target_libro"].copy()
    flags, summ = [], []
    for det, g in gate_result.items():
        if g["status"] not in ("calibrated", "preliminary") or f"ai_score__{det}" not in T:
            continue
        t = T[["passage_id", "page_start", "page_end", "chapter", f"ai_score__{det}"]].rename(
            columns={f"ai_score__{det}": "ai_score"})
        t["detector"], t["gate_status"] = det, g["status"]
        t["above_threshold"] = t.ai_score > g["threshold"]
        flags.append(t)
        for chap, sub in [("(todo el documento)", t)] + list(t.groupby("chapter")):
            lo, hi = expected_false_positive_interval(len(sub), *g["cv_fpr_ci"])
            summ.append({"detector": det, "gate_status": g["status"], "chapter": chap, "n_passages": len(sub),
                         "n_above_threshold": int(sub.above_threshold.sum()),
                         "detector_cv_fpr": round(g["cv_fpr"], 3),
                         "detector_cv_fpr_ci_low": round(g["cv_fpr_ci"][0], 3),
                         "detector_cv_fpr_ci_high": round(g["cv_fpr_ci"][1], 3),
                         "expected_if_all_human_low": lo, "expected_if_all_human_high": hi,
                         "exceeds_false_positive_range": int(sub.above_threshold.sum()) > hi})
    return (pd.concat(flags, ignore_index=True) if flags else pd.DataFrame(),
            pd.DataFrame(summ))


def statements(gate_result: dict, summary: pd.DataFrame) -> list[str]:
    """Plain-language results in the phrasing allowed by §32."""
    out = []
    for det, g in gate_result.items():
        label = DETECTORS[det]["label"]
        if g["status"] == "not_informative":
            out.append(f"{label}: no separó de forma fiable los textos humanos de los generados en el corpus de "
                       f"control ({'; '.join(g['reasons'])}). No se aplicó al informe.")
            continue
        if g["status"] == "not_run":
            continue
        row = summary[(summary.detector == det) & (summary.chapter == "(todo el documento)")]
        if row.empty:
            continue
        r = row.iloc[0]
        pre = "Resultado preliminar. " if g["status"] == "preliminary" else ""
        out.append(
            f"{pre}{label}: en el corpus de control tuvo una tasa de falsos positivos de {g['cv_fpr']:.0%} "
            f"(IC 95% {g['cv_fpr_ci'][0]:.0%}–{g['cv_fpr_ci'][1]:.0%}; validación cruzada por documento) y detectó {g['cv_tpr']:.0%} de los textos generados. "
            f"Marcó {r.n_above_threshold} de {r.n_passages} pasajes del informe como más parecidos a los textos "
            f"generados que el 95% de los textos humanos de control. Si todos los pasajes fueran humanos, "
            f"se esperarían entre {r.expected_if_all_human_low} y {r.expected_if_all_human_high} marcas por azar. "
            + ("El número supera ese rango: es compatible con el uso de herramientas de IA, pero también con "
               "diferencias de género, época o edición entre el informe y los textos de control. "
               if r.exceeds_false_positive_range else "El número está dentro de ese rango. ")
            + "Esto no permite atribuir ningún pasaje a una herramienta de IA.")
    return out


@dataclass
class CalibrationResult:
    metrics: pd.DataFrame
    gate: dict
    flags: pd.DataFrame
    summary: pd.DataFrame
    statements: list


def run_analysis(scores: pd.DataFrame) -> CalibrationResult:
    m = calibrate(scores)
    g = gate(m)
    flags, summary = apply_to_target(scores, g)
    return CalibrationResult(m, g, flags, summary, statements(g, summary))
