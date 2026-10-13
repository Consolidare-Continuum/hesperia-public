# HESPERIA — Contradiction calibration surface (Task 11).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import copy
from pathlib import Path

from hesperia.extensions.triz.contradiction_calibration import (
    get_default_contradiction_calibration,
    load_contradiction_calibration,
    validate_contradiction_calibration,
)
from hesperia.extensions.triz.contradiction_feedback import build_contradiction_feedback_signals


def _repo_cal_path() -> Path:
    # tests/triz -> repo root (…/hesperia/hesperia)
    return Path(__file__).resolve().parents[2] / "assets" / "data" / "engine_dynamics_v060" / "tfp" / "contradiction_calibration_v1.json"


def test_valid_calibration_profile_loads() -> None:
    p = _repo_cal_path()
    assert p.is_file()
    payload = load_contradiction_calibration(p)
    assert payload.get("profile_name")
    v = validate_contradiction_calibration(payload)
    assert v["ok"] is True


def test_invalid_values_rejected() -> None:
    base = get_default_contradiction_calibration()
    bad = copy.deepcopy(base)
    bad["activation"]["family_contradiction_influence"] = -0.5
    v = validate_contradiction_calibration(bad)
    assert v["ok"] is False
    assert any("negative" in e for e in v["errors"])

    bad2 = copy.deepcopy(base)
    del bad2["topology"]
    v2 = validate_contradiction_calibration(bad2)
    assert v2["ok"] is False


def test_activation_areas_change_with_area_influence() -> None:
    """``build_area_contradiction_pressure`` must respond to ``activation_cal`` (smooth compression)."""
    from hesperia.engine.tfp_signal_calibration import AREA_IDS
    from hesperia.extensions.triz.contradiction_coupling import build_area_contradiction_pressure

    af = {
        "c_x": ("A4", "F1"),
        "c_y": ("A7", "F1"),
    }
    rows = [
        {
            "pair": ["c_x", "c_y"],
            "raw_contradiction_score": 0.9,
            "effective_activation_score": 0.9,
            "confidence": 1.0,
        }
    ]
    act_lo = {"pressure_normalization_mode": "max"}
    act_hi = {"pressure_normalization_mode": "sum"}
    p_lo = build_area_contradiction_pressure(rows, af, AREA_IDS, activation_cal=act_lo)
    p_hi = build_area_contradiction_pressure(rows, af, AREA_IDS, activation_cal=act_hi)
    assert p_lo != p_hi


def test_topology_transition_metrics_differ() -> None:
    from hesperia.engine.tfp_signal_calibration import load_tfp_signal_calibration
    from hesperia.extensions.triz.topology_contradiction_coupling import compute_transition_pressure

    cfg = load_tfp_signal_calibration()
    area_ids = [str(x) for x in (cfg.get("area_ids") or [])]
    z = {a: 0.0 for a in area_ids}
    a_only = {**z, "A1": 1.0}
    b_only = {**z, "A2": 1.0}
    summaries = [
        {"area_contradiction_pressure": dict(a_only), "contradiction_load_normalized": 0.0},
        {"area_contradiction_pressure": dict(b_only), "contradiction_load_normalized": 1.0},
    ]
    low = {"transition_pressure_influence": 0.2}
    high = {"transition_pressure_influence": 2.0}
    t_low = compute_transition_pressure(summaries, area_ids, topology_cal=low)
    t_high = compute_transition_pressure(summaries, area_ids, topology_cal=high)
    assert t_low != t_high


def test_feedback_ranking_changes() -> None:
    rows = [
        {"pair": ["a", "b"], "raw_contradiction_score": 0.8, "effective_score": 0.2, "confidence": 0.2},
    ]
    unc = {"lexical_uncertainty": 0.1, "concept_uncertainty": 0.1, "fuzzy_link_ratio": 0.1}
    low = copy.deepcopy(get_default_contradiction_calibration())
    low["feedback"]["recurrence_influence"] = 0.1
    high = copy.deepcopy(get_default_contradiction_calibration())
    high["feedback"]["recurrence_influence"] = 2.0
    f_low = build_contradiction_feedback_signals(
        contradiction_rows=rows, uncertainty_package=unc, contradiction_calibration=low
    )
    f_high = build_contradiction_feedback_signals(
        contradiction_rows=rows, uncertainty_package=unc, contradiction_calibration=high
    )
    assert f_low["global_feedback_summary"]["calibration_contradiction_risk"] != f_high["global_feedback_summary"][
        "calibration_contradiction_risk"
    ]


def test_release_gating_thresholds_affect_verdict() -> None:
    from hesperia.extensions.triz.conflict_release_gating import _verdict_from_release_thresholds

    rg = {"pass_threshold": 0.85, "qualified_pass_threshold": 0.65}
    assert _verdict_from_release_thresholds(0.9, rg) == "PASS"
    assert _verdict_from_release_thresholds(0.7, rg) == "QUALIFIED_PASS"
    assert _verdict_from_release_thresholds(0.5, rg) == "FAIL"


def test_snapshot_and_usage_in_bundle_shape() -> None:
    from hesperia.extensions.triz.contradiction_calibration import build_calibration_snapshot, build_calibration_usage_trace

    cal = load_contradiction_calibration(_repo_cal_path())
    snap = build_calibration_snapshot(cal, source_path=str(_repo_cal_path()))
    assert snap.get("sha256") and snap.get("profile_name")
    usage = build_calibration_usage_trace(cal)
    assert "activation.pressure_normalization_mode" in usage or "version" in "".join(usage.keys())
