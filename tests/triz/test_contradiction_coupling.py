# HESPERIA — Tests for TFP contradiction coupling (v0.5.8 task 1).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import pytest

from hesperia.engine.tfp_signal_calibration import AREA_IDS
from hesperia.extensions.triz.contradiction_coupling import (
    apply_contradiction_coupling,
    build_area_contradiction_pressure,
    build_dynamic_inhibition_delta,
)
from hesperia.nlp.tfp_activation import build_invariant_tfp_activation


def _sample_af_two_areas() -> dict[str, tuple[str, str]]:
    return {
        "c_x": ("A4", "F1"),
        "c_y": ("A7", "F1"),
        "c_z": ("A4", "F2"),
    }


def test_pressure_normalized_two_areas() -> None:
    af = _sample_af_two_areas()
    contradictions = [
        {"pair": ["c_x", "c_y"], "raw_contradiction_score": 0.42},
    ]
    p = build_area_contradiction_pressure(contradictions, af, AREA_IDS)
    assert p["A4"] == pytest.approx(1.0)
    assert p["A7"] == pytest.approx(1.0)
    assert max(p.values()) == pytest.approx(1.0)
    for aid in AREA_IDS:
        if aid not in ("A4", "A7"):
            assert p[aid] == pytest.approx(0.0)


def test_dynamic_inhibition_delta_symmetric() -> None:
    af = _sample_af_two_areas()
    contradictions = [
        {"concept_a": "c_x", "concept_b": "c_y", "score": 0.5},
    ]
    delta = build_dynamic_inhibition_delta(contradictions, af, AREA_IDS)
    i4 = AREA_IDS.index("A4")
    i7 = AREA_IDS.index("A7")
    assert delta[i4][i7] == pytest.approx(delta[i7][i4])
    assert delta[i4][i7] == pytest.approx(1.0)
    n = len(AREA_IDS)
    for i in range(n):
        for j in range(n):
            if {i, j} != {i4, i7} and i != j:
                assert delta[i][j] == pytest.approx(0.0)


def test_activation_changes_with_contradictions() -> None:
    markers = [("B_A10_F10_001", 2.0), ("B_A1_F10_001", 2.0)]
    af = {
        "B_A10_F10_001": ("A4", "F1"),
        "B_A1_F10_001": ("A7", "F1"),
    }
    none_r = build_invariant_tfp_activation(
        markers,
        token_count=10,
        concept_to_area_family=af,
        contradictions=None,
    )
    with_r = build_invariant_tfp_activation(
        markers,
        token_count=10,
        concept_to_area_family=af,
        contradictions=[
            {"pair": ["B_A10_F10_001", "B_A1_F10_001"], "raw_contradiction_score": 0.9},
        ],
    )
    assert none_r["contradiction_coupling_active"] is False
    assert with_r["contradiction_coupling_active"] is True
    assert with_r["areas_inhibited"] != none_r["areas_inhibited"]
    assert with_r["areas_final"] != none_r["areas_final"]
    assert with_r["contradiction_count_used"] == 1


def test_no_contradictions_preserves_shape_and_deterministic_zeros() -> None:
    markers = [("B_A10_F10_001", 1.0)]
    af = {"B_A10_F10_001": ("A4", "F1")}
    out = build_invariant_tfp_activation(
        markers,
        token_count=5,
        concept_to_area_family=af,
        contradictions=None,
    )
    assert out["areas_pressure_adjusted"] == out["areas_raw"]
    assert sum(float(out["contradiction_pressure"][a]) for a in AREA_IDS) == pytest.approx(0.0)
    assert out["contradiction_coupling_active"] is False
    assert out["contradiction_count_used"] == 0
    z = out["dynamic_inhibition_delta"]
    assert all(z[i][j] == 0.0 for i in range(len(AREA_IDS)) for j in range(len(AREA_IDS)))


def test_same_area_contradiction_pressure() -> None:
    af = {
        "c_a": ("A4", "F1"),
        "c_b": ("A4", "F2"),
    }
    contradictions = [{"pair": ["c_a", "c_b"], "raw_contradiction_score": 0.33}]
    p = build_area_contradiction_pressure(contradictions, af, AREA_IDS)
    assert p["A4"] == pytest.approx(1.0)

    markers = [("c_a", 1.5), ("c_b", 1.5)]
    none_r = build_invariant_tfp_activation(
        markers,
        token_count=4,
        concept_to_area_family=af,
        contradictions=None,
    )
    with_r = build_invariant_tfp_activation(
        markers,
        token_count=4,
        concept_to_area_family=af,
        contradictions=contradictions,
    )
    assert with_r["contradiction_pressure"]["A4"] > 0.0
    assert with_r["areas_pressure_adjusted"]["A4"] < none_r["areas_raw"]["A4"]


def test_apply_coupling_returns_expected_keys() -> None:
    af = _sample_af_two_areas()
    raw = {a: 0.0 for a in AREA_IDS}
    raw["A4"] = 2.0
    raw["A7"] = 1.0
    pressure = build_area_contradiction_pressure(
        [{"pair": ["c_x", "c_y"], "raw_contradiction_score": 1.0}],
        af,
        AREA_IDS,
    )
    delta = build_dynamic_inhibition_delta(
        [{"pair": ["c_x", "c_y"], "raw_contradiction_score": 1.0}],
        af,
        AREA_IDS,
    )
    base = [[0.0 for _ in AREA_IDS] for _ in AREA_IDS]
    out = apply_contradiction_coupling(raw, base, pressure, delta, AREA_IDS, inhibition_scale=1.0)
    assert set(out.keys()) >= {
        "areas_pressure_adjusted",
        "inhibition_matrix_dynamic",
        "areas_inhibited",
        "contradiction_pressure",
        "dynamic_inhibition_delta",
    }
