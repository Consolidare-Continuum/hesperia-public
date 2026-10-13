# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Golden corpus smoke: deterministic extract counts (no API)."""

from __future__ import annotations

from pathlib import Path

from tools.dict_calibration.extract_lexical import extract_corpus

FIXTURE_CORPUS = Path(__file__).resolve().parent / "fixtures/dict_calibration/corpus"


def test_golden_corpus_extract_has_expected_ngrams() -> None:
    rows = extract_corpus(FIXTURE_CORPUS, min_freq=1)
    assert rows
    texts = {r["text"] for r in rows if r["pattern_type"] == "ngram"}
    assert "splitting" in texts
    assert "identity diffusion" in texts
