"""Detector calibration: passage building, metrics, gate and reporting guardrails."""

import re

import numpy as np
import pandas as pd
import pytest

from src import calibration as cal


def test_normalise_generated_strips_chat_formatting():
    raw = "## Título\n\n**Negrita** y *cursiva*.\n- punto uno\n1. punto dos\n“Texto final”"
    out = cal.normalise_generated(raw)
    assert "#" not in out and "**" not in out and "*" not in out
    assert out.startswith("Título Negrita y cursiva.")
    assert "- punto" not in out and "1. punto" not in out


def test_build_passages_bounds_and_break_key():
    sent = "La entidad ejecutó el presupuesto asignado para la vigencia. "
    paras = [{"page_start": i, "page_end": i, "chapter": "A" if i < 6 else "B", "text": sent * 8} for i in range(12)]
    out = cal.build_passages(paras, min_words=100, max_words=200, break_key="chapter")
    assert out and all(100 <= cal.n_words(p["text"]) <= 200 for p in out)
    assert all(p["chapter"] in ("A", "B") for p in out)
    for p in out:  # never crosses the chapter change at page 6
        assert not (p["page_start"] < 6 <= p["page_end"])


def test_auc_matches_sklearn():
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 300)
    s = rng.normal(size=300) + y
    s[:30] = 0.0  # ties
    assert cal.auc(y, s) == pytest.approx(roc_auc_score(y, s))


def _synthetic_scores(sep: float, n_gen: int = 3, n_src: int = 8, per_src: int = 10, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for k in range(n_src):
        for j in range(per_src):
            rows.append({"passage_id": f"H{k}-{j}", "corpus": "A_human", "source_id": f"H{k}", "generator": "human",
                         "prompt_id": None, "genre": "g", "period": "p1" if k % 2 else "p2", "artifact_rate": 0.0,
                         "binoculars": 1.0 + rng.normal(0, 0.05), "fast_detectgpt": rng.normal(0, 1),
                         "logppl_observer": 2.5 + rng.normal(0, 0.2)})
    for g in range(n_gen):
        for p in range(24):
            rows.append({"passage_id": f"B{g}-{p}", "corpus": "B_ai", "source_id": f"gen{g}", "generator": f"gen{g}",
                         "prompt_id": f"P{p:02d}", "genre": "g", "period": "generated", "artifact_rate": 0.0,
                         "binoculars": 1.0 - sep * 0.05 + rng.normal(0, 0.05), "fast_detectgpt": sep + rng.normal(0, 1),
                         "logppl_observer": 2.5 - sep * 0.2 + rng.normal(0, 0.2)})
    for t in range(40):
        rows.append({"passage_id": f"T{t:03d}", "corpus": "target_libro", "source_id": "LDV2026", "generator": None,
                     "prompt_id": None, "genre": "x", "period": "2026", "artifact_rate": 0.0,
                     "chapter": "II" if t < 20 else "IV", "page_start": t, "page_end": t,
                     "binoculars": 1.0 + rng.normal(0, 0.05), "fast_detectgpt": rng.normal(0, 1),
                     "logppl_observer": 2.5 + rng.normal(0, 0.2)})
    return pd.DataFrame(rows)


def test_grouped_cv_threshold_controls_false_positives():
    s = cal.oriented_scores(_synthetic_scores(sep=4.0))
    A, B = s[s.corpus == "A_human"], s[s.corpus == "B_ai"]
    cv = cal.grouped_cv_threshold(A.ai_score__fast_detectgpt, A.source_id, B.ai_score__fast_detectgpt, B.prompt_id)
    assert cv["cv_fpr"] <= 0.15
    assert cv["cv_tpr"] > 0.9


def test_gate_statuses():
    good = cal.gate(cal.calibrate(_synthetic_scores(sep=4.0)))
    assert good["fast_detectgpt"]["status"] == "calibrated"
    one_gen = cal.gate(cal.calibrate(_synthetic_scores(sep=4.0, n_gen=1)))
    assert one_gen["fast_detectgpt"]["status"] == "preliminary"
    useless = cal.gate(cal.calibrate(_synthetic_scores(sep=0.0)))
    assert all(v["status"] == "not_informative" for v in useless.values())


def test_uninformative_detector_is_not_applied_to_report():
    res = cal.run_analysis(_synthetic_scores(sep=0.0))
    assert res.flags.empty and res.summary.empty
    assert all("No se aplicó al informe" in s for s in res.statements)


def test_application_reports_counts_with_expected_false_positives():
    res = cal.run_analysis(_synthetic_scores(sep=4.0))
    whole = res.summary[(res.summary.detector == "fast_detectgpt") & (res.summary.chapter == "(todo el documento)")]
    assert len(whole) == 1 and whole.iloc[0].n_passages == 40
    r = whole.iloc[0]
    assert r.expected_if_all_human_low <= r.expected_if_all_human_high
    # The report passages are drawn like the human controls, so the count should stay in the chance range.
    assert not r.exceeds_false_positive_range


def test_statements_never_state_a_share_of_the_report_written_by_ai():
    forbidden = re.compile(r"\d+\s?%\s*(?:del|de)\s+(?:documento|informe|texto)|escrito en un \d+|\d+\s?%\s*IA", re.I)
    for sep in (0.0, 4.0):
        for s in cal.run_analysis(_synthetic_scores(sep=sep)).statements:
            assert not forbidden.search(s), s
            if "Marcó" in s:
                assert "no permite atribuir" in s


def test_artifact_rate_flags_extraction_debris():
    assert cal.artifact_rate("La entidad ejecutó el presupuesto.") == 0
    assert cal.artifact_rate("La enti dad ej3cutó b c d presupuesto") > 0


def test_detector_scores_on_logits():
    torch = pytest.importorskip("torch")
    from src import detectors as det
    torch.manual_seed(0)
    ids = torch.randint(0, 50, (40,))
    # A model that predicts the actual next token with high confidence -> high Fast-DetectGPT score.
    confident = torch.full((40, 50), -5.0)
    confident[torch.arange(39), ids[1:]] = 5.0
    uniform = torch.zeros(40, 50)
    assert det.fast_detectgpt_analytic(confident, ids) > det.fast_detectgpt_analytic(torch.randn(40, 50) * 3, ids)
    assert det.log_perplexity(uniform, ids) == pytest.approx(np.log(50), rel=1e-5)
    assert det.cross_perplexity(uniform, uniform, ids) == pytest.approx(np.log(50), rel=1e-5)
    assert det.binoculars(uniform, uniform, ids) == pytest.approx(1.0, rel=1e-5)


def test_tiny_random_pair_scores_a_passage():
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from src import detectors as det
    out = det.ModelPair.tiny_random().score("La entidad ejecutó el presupuesto asignado para la vigencia fiscal.", 128)
    assert out["n_tokens"] > 16 and not out["nonfinite"]
    assert set(["binoculars", "fast_detectgpt", "logppl_observer"]) <= set(out)


def test_gate_without_controls_is_not_run():
    g = cal.gate(pd.DataFrame())
    assert all(v["status"] == "not_run" for v in g.values())
