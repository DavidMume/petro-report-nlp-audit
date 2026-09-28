"""Tests for the exploratory authorship module's guardrails."""

import pandas as pd
import pytest

from src.authorship import apply_calibrated_detector, count_syllables_es, segment_document


@pytest.mark.parametrize("w,n", [("casa", 2), ("país", 2), ("contraloría", 5), ("gobierno", 3), ("ciudad", 2)])
def test_spanish_syllables(w, n):
    assert count_syllables_es(w) == n


def test_segments_never_cross_chapters():
    rows = []
    for ch in ("A", "B"):
        for i in range(120):
            rows.append({"chapter": ch, "level2": ch, "page": 1, "paragraph_id": f"{ch}{i}",
                         "clean_text": "palabra " * 12})
    segs = segment_document(pd.DataFrame(rows), target_words=500, min_words=300)
    assert set(segs.chapter) == {"A", "B"}
    for _, s in segs.iterrows():
        assert all(pid.startswith(s.chapter) for pid in s.paragraph_ids.split(";"))


def test_uncalibrated_detector_is_refused():
    with pytest.raises(ValueError, match="uncalibrated"):
        apply_calibrated_detector(pd.DataFrame(), "any-detector", {})
