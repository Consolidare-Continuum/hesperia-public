# HESPERIA — Tests for LEVEL 12 Longitudinal and session comparison
"""Compare two sessions, longitudinal curves, aggression/relational trends, structural change."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _session(session_id: str, areas: dict, families: dict | None = None):
    analysis = {"areas": areas, "families": families or {}, "concepts": {}}
    return {"session_id": session_id, "analysis": analysis}


def test_two_sessions_compared() -> None:
    from research.clinical_tfp.longitudinal import compare_session_activations

    a = _session("S01", {"A2": 0.5, "A3": 0.8, "A4": 0.9})
    b = _session("S02", {"A2": 0.6, "A3": 0.5, "A4": 0.4})
    out = compare_session_activations(a, b)
    assert "area_deltas" in out
    assert "family_deltas" in out
    assert "concept_deltas" in out
    assert out["area_deltas"]["A3"] == 0.5 - 0.8  # -0.3
    assert out["area_deltas"]["A4"] == 0.4 - 0.9  # -0.5
    assert out["area_deltas"]["A2"] == 0.6 - 0.5  # +0.1


def test_longitudinal_curves_built_correctly() -> None:
    from research.clinical_tfp.longitudinal import build_longitudinal_curves

    sessions = [
        _session("S01", {"A2": 0.2, "A3": 0.92, "A4": 0.81, "A7": 0.10}),
        _session("S02", {"A2": 0.3, "A3": 0.88, "A4": 0.79, "A7": 0.18}),
        _session("S03", {"A2": 0.4, "A3": 0.74, "A4": 0.54, "A7": 0.35}),
        _session("S04", {"A2": 0.5, "A3": 0.61, "A4": 0.30, "A7": 0.57}),
    ]
    curves = build_longitudinal_curves(sessions)
    assert "A2" in curves
    assert "A3" in curves
    assert "A4" in curves
    assert "A7" in curves
    assert "A10" in curves
    assert curves["A3"] == [0.92, 0.88, 0.74, 0.61]
    assert curves["A4"] == [0.81, 0.79, 0.54, 0.30]
    assert curves["A7"] == [0.10, 0.18, 0.35, 0.57]
    assert len(curves["A2"]) == 4


def test_aggression_trend_detected_correctly() -> None:
    from research.clinical_tfp.longitudinal import detect_aggression_trend

    sessions = [
        _session("S01", {"A4": 0.84}),
        _session("S02", {"A4": 0.77}),
        _session("S03", {"A4": 0.60}),
        _session("S04", {"A4": 0.39}),
    ]
    out = detect_aggression_trend(sessions)
    assert out["trend"] == "decreasing"
    assert out["curve"] == [0.84, 0.77, 0.60, 0.39]
    assert out["peak_session"] == "S01"

    increasing = [
        _session("S01", {"A4": 0.2}),
        _session("S02", {"A4": 0.5}),
    ]
    out_inc = detect_aggression_trend(increasing)
    assert out_inc["trend"] == "increasing"


def test_relational_capacity_trend_detected_correctly() -> None:
    from research.clinical_tfp.longitudinal import detect_relational_capacity_trend

    sessions = [
        _session("S01", {"A7": 0.12}),
        _session("S02", {"A7": 0.21}),
        _session("S03", {"A7": 0.34}),
        _session("S04", {"A7": 0.55}),
    ]
    out = detect_relational_capacity_trend(sessions)
    assert out["trend"] == "increasing"
    assert out["curve"] == [0.12, 0.21, 0.34, 0.55]
    assert "evidence" in out
    assert "gratitude" in out["evidence"] or "repair_capacity" in out["evidence"]


def test_structural_change_summary_produced() -> None:
    from research.clinical_tfp.longitudinal import analyze_treatment_trajectory

    # Example from spec: S01–S04 with A3 down, A4 down, A7 up → moderate_positive
    sessions = [
        _session("S01", {"A3": 0.95, "A4": 0.88, "A7": 0.10}),
        _session("S02", {"A3": 0.82, "A4": 0.70, "A7": 0.18}),
        _session("S03", {"A3": 0.69, "A4": 0.52, "A7": 0.31}),
        _session("S04", {"A3": 0.55, "A4": 0.33, "A7": 0.49}),
    ]
    result = analyze_treatment_trajectory(sessions)
    assert result["session_count"] == 4
    assert "curves" in result
    assert "defense_evolution" in result
    assert result["aggression_trend"]["trend"] == "decreasing"
    assert result["relational_capacity_trend"]["trend"] == "increasing"
    sc = result["structural_change"]
    assert sc["structural_change"] == "moderate_positive"
    assert "confidence" in sc
    assert "supporting_factors" in sc
    assert "reduced aggression" in sc["supporting_factors"]
    assert "improved relational capacity" in sc["supporting_factors"]


def test_export_trajectory_json() -> None:
    from research.clinical_tfp.longitudinal import analyze_treatment_trajectory, export_trajectory_json

    sessions = [
        _session("S01", {"A3": 0.8, "A4": 0.7, "A7": 0.2}),
        _session("S02", {"A3": 0.5, "A4": 0.4, "A7": 0.5}),
    ]
    result = analyze_treatment_trajectory(sessions)
    js = export_trajectory_json(result)
    parsed = json.loads(js)
    assert parsed["session_count"] == 2
    assert "structural_change" in parsed


def test_export_trajectory_markdown() -> None:
    from research.clinical_tfp.longitudinal import analyze_treatment_trajectory, export_trajectory_markdown

    sessions = [_session("S01", {"A4": 0.5})]
    result = analyze_treatment_trajectory(sessions)
    md = export_trajectory_markdown(result)
    assert "# Траектория лечения" in md
    assert "Количество сессий" in md
    assert "Структурное изменение" in md
