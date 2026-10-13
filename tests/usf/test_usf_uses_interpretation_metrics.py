# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
USF must include canonical interpretation fields from interpretation_metrics.
"""

from __future__ import annotations

import pytest

from sphere.usf.usf_generator import build_usf_object


def _minimal_raw_metrics():
    return {
        "area_vector": [1/12] * 12,
        "family_counts": [1/288] * 288,
        "family_peaks": list(range(5)),
        "dominant_area": 0,
        "dominant_family": 0,
        "entropy": 0.5,
        "tension": 0.5,
        "loopability": 0.0,
        "coverage": 0.1,
    }


def _minimal_dynamism():
    return {
        "trajectory": {},
        "transition_matrix": [[0] * 12 for _ in range(12)],
        "curvature": 0.0,
        "jump_rate": 0.0,
        "stability_index": 0.0,
    }


def _minimal_propagation():
    return {
        "propagated_area_vector": [1/12] * 12,
        "propagated_family_counts": [1/288] * 288,
    }


def _minimal_logic_outputs():
    return {"triggered_rules": [], "logic_flags": [], "structural_diagnostics": []}


def _minimal_provenance():
    return {"created_at": "", "pipeline_version": "v1", "input_hash": "x", "deterministic": True}


def test_usf_includes_structural_state_when_interpretation_provided():
    interp = {
        "structural_state": "focused_dominant",
        "dominant_area_id": 0,
        "dominance_strength": 0.4,
        "entropy_state": "reduced_after_shadow",
        "tension_state": "normal",
        "propagation_state": "moderate_spread",
        "active_events": ["dominant_area"],
        "interpretation_flags": ["stable_focus"],
        "event_summary": {"total_triggered": 1},
        "interpretation_diagnostics": {},
    }
    usf = build_usf_object(
        "doc1",
        {},
        _minimal_raw_metrics(),
        _minimal_dynamism(),
        _minimal_propagation(),
        _minimal_logic_outputs(),
        _minimal_provenance(),
        interpretation_metrics=interp,
    )
    assert usf["structural_state"] == "focused_dominant"
    assert usf["active_events"] == ["dominant_area"]
    assert usf["interpretation_flags"] == ["stable_focus"]
    assert "fingerprint" in usf
    assert usf["fingerprint"]["structural_state"] == "focused_dominant"
    assert "compatibility" in usf
    assert usf["compatibility"]["legacy_logic_bridge_used"] is False


def test_usf_canonical_fields_from_interpretation_only():
    interp = {
        "structural_state": "diffuse_spread",
        "dominant_area_id": 2,
        "dominance_strength": 0.15,
        "active_events": ["propagation_spread"],
        "interpretation_flags": ["diffusion_noise_controlled"],
        "event_summary": {},
        "interpretation_diagnostics": {},
    }
    usf = build_usf_object(
        "doc2",
        {},
        _minimal_raw_metrics(),
        _minimal_dynamism(),
        _minimal_propagation(),
        _minimal_logic_outputs(),
        _minimal_provenance(),
        interpretation_metrics=interp,
    )
    assert usf["structural_state"] == "diffuse_spread"
    assert usf["dominant_area_id"] == 2
    assert usf["dominance_strength"] == 0.15
    assert "propagation_spread" in usf["active_events"]
