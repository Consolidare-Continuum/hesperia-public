# HESPERIA — Tests for LEVEL 10 Session topology (temporal dynamics)

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _synthetic_indexes() -> tuple[dict[str, list[tuple[str, float]]], dict[str, tuple[str, str]]]:
    marker_index = {
        "attack": [("B_A10_F10_001", 1.0)],
        "repair": [("B_A1_F10_001", 1.0)],
        "control": [("B_A10_F10_002", 1.0)],
        "shame": [("B_A1_F10_002", 1.0)],
    }
    af = {
        "B_A10_F10_001": ("A4", "F1"),
        "B_A1_F10_001": ("A7", "F1"),
        "B_A10_F10_002": ("A5", "F1"),
        "B_A1_F10_002": ("A2", "F1"),
    }
    return marker_index, af


def test_segmentation_works() -> None:
    from research.clinical_tfp.session_topology import segment_session

    assert segment_session("") == []
    assert segment_session("  ", window_size=80) == []

    text = "Пациент говорит спокойно."
    segs = segment_session(text, window_size=80)
    assert len(segs) == 1

    words = ["слово"] * 200
    long_text = " ".join(words)
    segs = segment_session(long_text, window_size=80)
    assert len(segs) == 3
    assert len(segs[0].split()) == 80
    assert len(segs[1].split()) == 80
    assert len(segs[2].split()) == 40


def test_segment_analysis_returns_results() -> None:
    from research.clinical_tfp.session_topology import analyze_session_segments

    marker_index, af = _synthetic_indexes()
    text = "attack repair control shame"
    results = analyze_session_segments(
        text,
        window_size=2,
        marker_index=marker_index,
        concept_to_area_family=af,
        phrase_index={},
    )
    assert isinstance(results, list)
    assert len(results) >= 1
    for row in results:
        assert "areas" in row
        assert "areas_raw" in row
        assert "areas_inhibited" in row
        assert "families" in row
        assert "concepts" in row


def test_transitions_detected_correctly() -> None:
    from research.clinical_tfp.session_topology import detect_state_transitions

    segs = [{"areas": {"A2": 0.5}}, {"areas": {"A2": 0.6}}]
    assert detect_state_transitions(segs) == []

    segs = [
        {"areas": {"A2": 0.8, "A3": 0.2}},
        {"areas": {"A2": 0.2, "A3": 0.9}},
    ]
    assert detect_state_transitions(segs) == [["A2", "A3"]]


def test_extract_and_build_area_curves() -> None:
    from research.clinical_tfp.session_topology import AREA_CURVE_MAP, build_area_curves, extract_area_curve

    segs = [
        {"areas": {"A2": 0.1, "A4": 0.4, "A7": 0.2}},
        {"areas": {"A2": 0.3, "A4": 0.5, "A5": 0.9}},
    ]
    assert extract_area_curve(segs, "A4") == [0.4, 0.5]
    curves = build_area_curves(segs)
    assert set(curves.keys()) == set(AREA_CURVE_MAP.keys())
    assert curves["aggression"] == [0.4, 0.5]
    assert curves["anxiety"] == [0.1, 0.3]
    assert curves["control"] == [0.0, 0.9]


def test_postprocess_area_curves_uses_momentum_and_session_center() -> None:
    from research.clinical_tfp.session_topology import postprocess_area_curves

    segs = [
        {"areas": {"A4": 0.2, "A2": 0.8}},
        {"areas": {"A4": 0.7, "A2": 0.3}},
        {"areas": {"A4": 0.9, "A2": 0.1}},
    ]
    curves, meta, rel, _stable_segs = postprocess_area_curves(segs, session_center_curves=True)
    assert meta["area_competition"] == "invariant_softmax"
    assert meta["temporal_momentum"]["alpha1"] > 0
    assert len(curves["aggression"]) == 3
    assert curves["aggression"][0] <= curves["aggression"][1] <= curves["aggression"][2]
    assert curves["aggression"] != [0.2, 0.7, 0.9]
    mu = sum(curves["aggression"]) / len(curves["aggression"])
    assert rel["aggression"][0] == pytest.approx(curves["aggression"][0] - mu)


def test_build_session_state_sequence() -> None:
    from research.clinical_tfp.session_topology import build_session_state_sequence

    segs = [
        {"areas": {"A2": 0.9}},
        {"areas": {"A3": 0.8}},
        {"areas": {"A3": 0.7}},
        {"areas": {"A4": 0.9}},
    ]
    assert build_session_state_sequence(segs) == ["A2", "A3", "A3", "A4"]


def test_detect_defense_shifts() -> None:
    from research.clinical_tfp.session_topology import detect_defense_shifts

    segs = [
        {"families": {"A3_F1": 0.9}},
        {"families": {"A3_F5": 0.8}},
        {"families": {"A2_F1": 0.5}},
    ]
    timeline = detect_defense_shifts(segs)
    assert timeline == ["splitting", "projective_identification", ""]


def test_run_session_topology_output_structure() -> None:
    from research.clinical_tfp.session_topology import run_session_topology

    marker_index, af = _synthetic_indexes()
    text = "repair repair attack attack control attack shame attack"
    out = run_session_topology(
        text,
        window_size=2,
        marker_index=marker_index,
        concept_to_area_family=af,
        phrase_index={},
    )
    assert "segments" in out
    assert "segments_stable" in out
    assert "transitions" in out
    assert "area_curves" in out
    assert "area_curves_raw" in out
    assert "area_curves_stable" in out
    assert "aggression_curve" in out
    assert "aggression_curve_raw" in out
    assert "state_sequence" in out
    assert "defense_timeline" in out
    assert "curve_projection_meta" in out
    assert "area_curves_session_relative" in out
    cpm = out["curve_projection_meta"]
    assert cpm.get("calibration_reference_bands", {}).get("low_tension") == 0.2
    assert cpm.get("engine_params", {}).get("area_competition") == "invariant_softmax"
    assert cpm.get("temporal_momentum", {}).get("alpha1") > 0
    assert isinstance(cpm.get("segment_dominance_confidence_raw"), list)
    assert isinstance(cpm.get("segment_dominance_confidence_stable"), list)
    assert out["aggression_curve"] == out["area_curves"]["aggression"]
    assert out["aggression_curve_raw"] == out["area_curves_raw"]["aggression"]
