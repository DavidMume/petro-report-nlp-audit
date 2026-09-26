"""Minimal tests for src/preprocess.py."""

import pytest

from src.preprocess import normalise_unicode, segment_sentences, tokenize


def test_normalise_unicode_is_idempotent():
    text = "informe económico y político"
    once = normalise_unicode(text)
    twice = normalise_unicode(once)
    assert once == twice


def test_normalise_unicode_preserves_spanish_accents():
    text = "inflación, tasación, año"
    result = normalise_unicode(text)
    assert "inflación" in result
    assert "año" in result


def test_segment_sentences_not_yet_implemented():
    with pytest.raises(NotImplementedError):
        segment_sentences("Esta es una oración. Esta es otra.")


def test_tokenize_not_yet_implemented():
    with pytest.raises(NotImplementedError):
        tokenize("Esta es una oración de prueba.")
