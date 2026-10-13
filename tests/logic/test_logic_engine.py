# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-9 compute_logic_metrics and structural rule integration.
"""

from __future__ import annotations

import numpy as np
import pytest

from sphere.logic.rule_engine import compute_logic_metrics


def _make_shadow_metrics(corrected_area_vector, corrected_family_counts, shadow_diagnostics):
    return {
        "corrected_area_vector": list(corrected_area_vector),
        "corrected_family_counts": list(corrected_family_counts),
        "shadow_diagnostics": shadow_diagnostics,
    }


def _make_propagation_metrics(propagation_diagnostics=None):
    return {
        "propagated_area_vector": [1/12] * 12,
        "propagated_family_counts": [1/288] * 288,
        "propagation_diagnostics": propagation_diagnostics or {},
    }


def _make_dynamism_metrics():
    return {
        "stability_index": 0.0,
        "jump_rate": {"jump_rate": 0.0},
        "curvature": 0.0,
    }


def test_compute_logic_metrics_returns_canonical_structure():
    shadow = _make_shadow_metrics(
        np.ones(12) / 12,
        np.ones(288) / 288,
        {"entropy_before": 3.0, "entropy_after": 2.5, "tension_before": 0.5, "tension_after": 0.6},
    )
    prop = _make_propagation_metrics({"active_edges_count": 24})
    dyn = _make_dynamism_metrics()
    out = compute_logic_metrics(shadow, prop, dyn)
    assert "triggered_rules" in out
    assert "dominance_events" in out
    assert "entropy_events" in out
    assert "tension_events" in out
    assert "anomaly_flags" in out
    assert "logic_diagnostics" in out
    assert "rules_evaluated_count" in out["logic_diagnostics"]
    assert "rules_triggered_count" in out["logic_diagnostics"]
    assert "dominant_area" in out["logic_diagnostics"]


def test_no_trigger_on_uniform_vector():
    shadow = _make_shadow_metrics(
        np.ones(12) / 12,
        np.ones(288) / 288,
        {"entropy_before": 3.0, "entropy_after": 3.0, "tension_before": 0.9, "tension_after": 0.9},
    )
    prop = _make_propagation_metrics({"active_edges_count": 0})
    dyn = _make_dynamism_metrics()
    out = compute_logic_metrics(shadow, prop, dyn)
    # Uniform: no dominant area share >= 0.35, no entropy drop, no tension increase, no spread
    assert out["logic_diagnostics"]["rules_triggered_count"] == 0
    assert out["triggered_rules"] == []
