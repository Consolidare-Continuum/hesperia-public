# HESPERIA — RAD. Ethan PO-01 unified text prep.
from __future__ import annotations

from core.lexical.analysis_input import prepare_structural_analysis_text


def test_prepare_identical_fingerprint_for_whitespace_and_case() -> None:
    """PO-01: shared prep collapses case/whitespace; punctuation unchanged (Cyrillic gold corpora safe)."""
    t1 = "Justice   FAIRNESS\nand order"
    t2 = "justice fairness and order"
    c1, m1 = prepare_structural_analysis_text(t1)
    c2, m2 = prepare_structural_analysis_text(t2)
    assert c1 == c2
    assert m1["analysis_text_fingerprint"] == m2["analysis_text_fingerprint"]
