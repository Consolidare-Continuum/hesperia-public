# HESPERIA — TFP-ENF-01: behavioral invariants (dominance, competition law, length scale, modifiers).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.dynamics.numeric import quantize

from hesperia.engine.concept_dictionary.executor import apply_cd_phase1, apply_saturation
from hesperia.engine.hesperia_control.dominance import classify_segment_dominance
from hesperia.engine.hesperia_control.modifier_mvp import apply_modifier_mvp_pre_cd


def test_dominance_single_clear_peak() -> None:
    """Top-two mass small vs total → weak_dominant; still a single top area (no dual peak)."""
    out, top, pair = classify_segment_dominance({"A1": 0.7, "A2": 0.1, "A3": 0.05})
    assert out in ("dominant", "weak_dominant")
    assert top == "A1"
    assert pair is not None
    assert pair[0] == "A1"


def test_dominance_mixed_when_gap_too_small() -> None:
    out, top, _pair = classify_segment_dominance({"A1": 0.35, "A2": 0.34})
    assert out == "mixed"
    assert top == "A1"


def test_softmax_competition_co_occurs_closed_form(tmp_path: Path) -> None:
    """Phase-2 co_occurs boost matches executor law (share-based competition term)."""
    p = tmp_path / "cd.jsonl"
    rows = [
        {
            "concept_id": "*",
            "type": "state",
            "activation": {"base_weight": 1.0, "cap": 10.0, "saturation_k": 1.0, "threshold": 0.0},
            "constraints": {"requires": [], "excludes": [], "co_occurs": []},
            "effects": {"amplifies": {}, "inhibits": {}},
        },
        {
            "concept_id": "B_A",
            "type": "state",
            "activation": {"base_weight": 1.0, "cap": 10.0, "saturation_k": 1.0, "threshold": 0.0},
            "constraints": {"requires": [], "excludes": [], "co_occurs": ["B_Z"]},
            "effects": {"amplifies": {}, "inhibits": {}},
        },
        {
            "concept_id": "B_Z",
            "type": "state",
            "activation": {"base_weight": 1.0, "cap": 10.0, "saturation_k": 1.0, "threshold": 0.0},
            "constraints": {"requires": [], "excludes": [], "co_occurs": []},
            "effects": {"amplifies": {}, "inhibits": {}},
        },
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    w = {"B_A": 1.0, "B_Z": 1.0}
    e = {"B_A": 2, "B_Z": 2}
    alpha, beta, eps = 0.25, 0.15, 1e-9
    snap_pre_soft = {"B_A": 2.0, "B_Z": 2.0}
    total_w = sum(snap_pre_soft.values())
    denom = eps + total_w
    s_co = 2.0
    penalty = 1.0 / (1.0 + alpha * 0.0)
    boost = 1.0 + beta * min(1.0, s_co / denom)
    expected_b_a = quantize(2.0 * penalty * boost)
    full = apply_cd_phase1(w, e, p, cd_phase=2)
    assert full["B_A"] == pytest.approx(expected_b_a)
    assert full["B_Z"] == pytest.approx(2.0)


def test_length_invariance_saturation_identity_scales_with_evidence(tmp_path: Path) -> None:
    """Under saturation_k=1 (identity), doubling evidence doubles raw score until cap."""
    p = tmp_path / "cd.jsonl"
    row = {
        "concept_id": "*",
        "type": "state",
        "activation": {"base_weight": 1.0, "cap": 100.0, "saturation_k": 1.0, "threshold": 0.0},
        "constraints": {"requires": [], "excludes": [], "co_occurs": []},
        "effects": {"amplifies": {}, "inhibits": {}},
    }
    p.write_text(json.dumps(row) + "\n", encoding="utf-8")
    half = apply_cd_phase1({"B_X": 1.0}, {"B_X": 1}, p, cd_phase=1)
    dbl = apply_cd_phase1({"B_X": 1.0}, {"B_X": 2}, p, cd_phase=1)
    assert half["B_X"] == pytest.approx(1.0)
    assert dbl["B_X"] == pytest.approx(2.0)


def test_length_invariance_saturation_compresses_large_scores() -> None:
    assert apply_saturation(10.0, 0.5) < 10.0
    assert apply_saturation(10.0, 1.0) == pytest.approx(10.0)


def test_modifier_propagation_negation_and_damping() -> None:
    w: dict[str, float] = {"B_a": 10.0, "B_b": 4.0}
    apply_modifier_mvp_pre_cd(w, negation_targets={"B_a": 1.0}, damping_factor=0.5)
    assert w["B_a"] == pytest.approx(0.0)
    assert w["B_b"] == pytest.approx(2.0)
