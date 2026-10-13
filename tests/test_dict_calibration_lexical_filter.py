# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from tools.dict_calibration.lexical_filter import filter_rows_for_llm


def test_filter_drops_ru_stopword_unigrams() -> None:
    rows = [
        {"text": "что", "normalized": "что", "pattern_type": "ngram", "freq": 9000},
        {"text": "abandonment panic", "normalized": "abandonment panic", "pattern_type": "ngram", "freq": 3},
    ]
    out = filter_rows_for_llm(rows)
    texts = {r["text"] for r in out}
    assert "что" not in texts
    assert "abandonment panic" in texts


def test_filter_keeps_dep_modal() -> None:
    rows = [{"text": "x y", "lemma": "a|b", "pattern_type": "dep", "freq": 1}]
    assert filter_rows_for_llm(rows) == rows
