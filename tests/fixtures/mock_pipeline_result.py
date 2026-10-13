# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# See LEGAL_NOTICE.md for full terms.

"""Factory for mock pipeline results — used by fpf_bridge tests."""

from __future__ import annotations

import copy
from typing import Any


def make_pipeline_result(**overrides: Any) -> dict[str, Any]:
    """Build a realistic pipeline result dict with overridable nested keys.

    Defaults represent a focused_dominant baseline with area A2 dominant.
    """
    base: dict[str, Any] = {
        "document_id": "test_doc_001",
        "layer_outputs": {},
        "usf": {},
        "pipeline_metadata": {
            "pipeline_version": "v1",
            "deterministic": True,
            "executed_layers": list(range(1, 11)),
        },
        "diagnostics": {},
        "shadow_metrics": {
            "corrected_area_vector": [
                0.05, 0.02, 0.50, 0.10, 0.03,
                0.05, 0.05, 0.02, 0.08, 0.03,
                0.04, 0.03,
            ],
            "corrected_family_counts": [0.0] * 288,
            "shadow_diagnostics": {
                "entropy_before": 2.5,
                "entropy_after": 2.0,
                "tension_before": 0.3,
                "tension_after": 0.3,
            },
        },
        "logic_metrics": {
            "triggered_rules": [
                {"type": "dominant_area", "area_id": 2, "share": 0.50},
                {"type": "entropy_drop", "delta_entropy": 0.20},
            ],
            "dominance_events": [{"type": "dominant_area", "area_id": 2}],
            "entropy_events": [{"type": "entropy_drop", "delta_entropy": 0.2}],
            "tension_events": [],
            "anomaly_flags": [],
            "logic_diagnostics": {
                "rules_evaluated_count": 5,
                "rules_triggered_count": 2,
                "dominant_area_id": 2,
                "entropy_after_shadow": 2.0,
                "tension_after_shadow": 0.3,
                "propagation_spread": 0,
            },
        },
        "interpretation_metrics": {
            "structural_state": "focused_dominant",
            "dominant_area_id": 2,
            "dominance_strength": 0.50,
            "entropy_state": "reduced_after_shadow",
            "tension_state": "normal",
            "propagation_state": "minimal_spread",
            "active_events": ["dominant_area", "entropy_drop"],
            "interpretation_flags": ["structural_concentration"],
            "event_summary": {},
            "interpretation_diagnostics": {},
        },
        "prolog_logic": {
            "derived_facts": [
                {"predicate": "structural_focus", "args": []},
            ],
            "rule_traces": [
                {
                    "rule": "structural_focus_rule",
                    "premises": ["dominant_area", "entropy_drop"],
                    "derived": "structural_focus",
                    "iteration": 1,
                },
            ],
            "prolog_diagnostics": {
                "iterations": 1,
                "facts_initial": 2,
                "facts_final": 3,
                "rules_fired": 1,
            },
        },
        "guards": {
            "sigma": {"passed": True, "failed_checks": [], "passed_checks": ["all"]},
            "gamma": {"passed": True, "failed_checks": [], "passed_checks": ["all"]},
            "theta": {
                "approved": True,
                "status": "approved",
                "violations": [],
                "warnings": [],
                "governance_flags": [],
            },
        },
        "dynamism_metrics": {
            "stability_index": 0.80,
            "curvature": 0.10,
            "jump_rate": 0.05,
            "trajectory": {"raw": [], "compressed": []},
            "transition_matrix": [[0] * 12 for _ in range(12)],
        },
    }

    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key].update(value)
        else:
            result[key] = value
    return result
