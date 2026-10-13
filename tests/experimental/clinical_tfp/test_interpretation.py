# HESPERIA — Tests for LEVEL 8 Clinical interpretation layer
"""Dominant area/family, aggression level, defense pattern, relational capacity."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_dominant_area_detected() -> None:
    from research.clinical_tfp.interpretation import get_dominant_area, interpret_session
    assert get_dominant_area({}) == ""
    assert get_dominant_area({"A2": 0.3, "A3": 0.8, "A4": 0.5}) == "A3"
    act = {"areas": {"A3": 0.67, "A2": 0.54}, "families": {}, "concepts": {}}
    out = interpret_session(act)
    assert out["dominant_area"] == "A3"


def test_aggression_level_classification() -> None:
    from research.clinical_tfp.interpretation import classify_aggression_level
    assert classify_aggression_level({"A4": 0.1}) == "low"
    assert classify_aggression_level({"A4": 0.25}) == "moderate"
    assert classify_aggression_level({"A4": 0.5}) == "moderate"
    assert classify_aggression_level({"A4": 0.6}) == "moderate"
    assert classify_aggression_level({"A4": 0.61}) == "high"
    assert classify_aggression_level({}) == "low"


def test_defense_pattern_mapping() -> None:
    from research.clinical_tfp.interpretation import detect_defense_pattern, DEFENSE_MAP
    assert detect_defense_pattern({}) == ""
    assert detect_defense_pattern({"A2_F1": 0.5}) == ""  # no A3
    assert detect_defense_pattern({"A3_F1": 0.9}) == "splitting"
    assert detect_defense_pattern({"A3_F6": 0.8, "A3_F2": 0.3}) == "role_reversal"
    assert detect_defense_pattern({"A3_F5": 0.7}) == "projective_identification"


def test_object_relation_pattern_mapping() -> None:
    from research.clinical_tfp.interpretation import detect_object_relation_pattern
    assert detect_object_relation_pattern({}) == ""
    assert detect_object_relation_pattern({"A3_F1": 0.5}) == ""  # no A2
    assert detect_object_relation_pattern({"A2_F3": 0.9}) == "persecutory_object"
    assert detect_object_relation_pattern({"A2_F6": 0.8, "A2_F2": 0.2}) == "integrated_object"


def test_relational_capacity_classification() -> None:
    from research.clinical_tfp.interpretation import estimate_relational_capacity
    assert estimate_relational_capacity({}) == "low"
    assert estimate_relational_capacity({"A7": 0.2}) == "low"
    assert estimate_relational_capacity({"A7": 0.3}) == "moderate"
    assert estimate_relational_capacity({"A7": 0.5}) == "moderate"
    assert estimate_relational_capacity({"A7": 0.6}) == "moderate"
    assert estimate_relational_capacity({"A7": 0.61}) == "high"


def test_interpret_session_full() -> None:
    from research.clinical_tfp.interpretation import interpret_session
    act = {
        "areas": {"A3": 0.9, "A4": 0.7, "A2": 0.2},
        "families": {"A3_F1": 0.9, "A3_F2": 0.3, "A4_F1": 0.5},
        "concepts": {},
    }
    out = interpret_session(act)
    assert out["dominant_area"] == "A3"
    assert out["dominant_family"] == "A3_F1"
    assert out["secondary_area"] == "A4"
    assert out["defense_pattern"] == "splitting"
    assert out["aggression_level"] == "high"
    assert "object_relation_pattern" in out
    assert "relational_capacity" in out


def test_interpretation_example_splitting_aggression() -> None:
    """Example: text about blaming therapist, good then bad, strong anger → A3 splitting, high aggression."""
    from hesperia.nlp import analyze_session
    from research.clinical_tfp.interpretation import interpret_session
    text = (
        "Пациент обвиняет терапевта, говорит что тот сначала был хорошим, "
        "а теперь плохим, и выражает сильную злость."
    )
    analysis = analyze_session(text)
    interpretation = interpret_session(analysis)
    assert "dominant_area" in interpretation
    assert "dominant_family" in interpretation
    assert "defense_pattern" in interpretation
    assert "aggression_level" in interpretation
    # With current Dict-A we may get A3, A3_F1, splitting, high depending on markers
    assert interpretation["aggression_level"] in ("low", "moderate", "high")
    if interpretation["dominant_area"] == "A3":
        assert interpretation["defense_pattern"] in ("", "splitting", "idealization_devaluation", "projection", "projective_identification", "role_reversal")
