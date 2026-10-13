# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-10 compute_interpretation_metrics and canonical structure.
"""

from __future__ import annotations

import pytest

from sphere.interpretation.engine import compute_interpretation_metrics


def _shadow_metrics(entropy_before=3.0, entropy_after=2.5, tension_before=0.5, tension_after=0.6):
    return {
        "corrected_area_vector": [0.4] + [0.06] * 11,
        "corrected_family_counts": [0.01] * 288,
        "shadow_diagnostics": {
            "entropy_before": entropy_before,
            "entropy_after": entropy_after,
            "tension_before": tension_before,
            "tension_after": tension_after,
        },
    }


def _logic_metrics(triggered_types=None):
    triggered = [{"type": t} for t in (triggered_types or [])]
    return {
        "triggered_rules": triggered,
        "dominance_events": [],
        "entropy_events": [],
        "tension_events": [],
        "anomaly_flags": [],
        "logic_diagnostics": {
            "dominant_area_id": 0,
            "rules_triggered_count": len(triggered_types or []),
        },
    }


def _propagation_metrics(active_edges=24):
    return {
        "propagated_area_vector": [1/12] * 12,
        "propagated_family_counts": [1/288] * 288,
        "propagation_diagnostics": {"active_edges_count": active_edges},
    }


def _dynamism_metrics():
    return {"stability_index": 0.0, "jump_rate": 0.0, "curvature": 0.0}


def test_interpretation_metrics_canonical_structure():
    out = compute_interpretation_metrics(
        _logic_metrics(),
        _shadow_metrics(),
        _propagation_metrics(),
        _dynamism_metrics(),
    )
    assert "structural_state" in out
    assert "dominant_area_id" in out
    assert "dominance_strength" in out
    assert "entropy_state" in out
    assert "tension_state" in out
    assert "propagation_state" in out
    assert "active_events" in out
    assert "interpretation_flags" in out
    assert "event_summary" in out
    assert "interpretation_diagnostics" in out


def test_focused_dominant_state():
    shadow = _shadow_metrics(entropy_after=2.0)
    shadow["corrected_area_vector"] = [0.5] + [0.05] * 11
    logic = _logic_metrics(triggered_types=["dominant_area"])
    logic["logic_diagnostics"]["dominant_area_id"] = 0
    out = compute_interpretation_metrics(logic, shadow, _propagation_metrics(), _dynamism_metrics())
    assert out["structural_state"] == "focused_dominant"
    assert "structural_concentration" in out["interpretation_flags"] or "stable_focus" in out["interpretation_flags"]


def test_unstable_transition_state():
    logic = _logic_metrics(triggered_types=["dominance_transition"])
    out = compute_interpretation_metrics(logic, _shadow_metrics(), _propagation_metrics(), _dynamism_metrics())
    assert out["structural_state"] == "unstable_transition"
    assert "transition_risk" in out["interpretation_flags"]


def test_tension_elevated():
    shadow = _shadow_metrics(tension_before=0.3, tension_after=0.5)
    logic = _logic_metrics(triggered_types=["tension_increase"])
    logic["tension_events"] = [{"type": "tension_increase", "delta_tension": 0.2}]
    out = compute_interpretation_metrics(logic, shadow, _propagation_metrics(), _dynamism_metrics())
    assert out["tension_state"] == "elevated"
    assert "elevated_tension" in out["interpretation_flags"]
