# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
USF backward compatibility: without interpretation_metrics, build still works.
Canonical fields present when interpretation_metrics provided.
"""

from __future__ import annotations

import pytest

from sphere.usf.usf_generator import build_usf_object, generate_usf


def _minimal_inputs():
    return {
        "document_id": "doc1",
        "source_metadata": {},
        "raw_metrics": {
            "area_vector": [1/12] * 12,
            "family_counts": [1/288] * 288,
            "family_peaks": [0, 1, 2, 3, 4],
            "dominant_area": 0,
            "dominant_family": 0,
            "entropy": 0.5,
            "tension": 0.5,
            "loopability": 0.0,
            "coverage": 0.1,
        },
        "dynamism_metrics": {
            "trajectory": {},
            "transition_matrix": [[0] * 12 for _ in range(12)],
            "curvature": 0.0,
            "jump_rate": 0.0,
            "stability_index": 0.0,
        },
        "propagation_metrics": {
            "propagated_area_vector": [1/12] * 12,
            "propagated_family_counts": [1/288] * 288,
        },
        "logic_outputs": {"triggered_rules": [], "logic_flags": [], "structural_diagnostics": []},
        "provenance": {"created_at": "", "pipeline_version": "v1", "input_hash": "x", "deterministic": True},
    }


def test_build_without_interpretation_metrics_succeeds():
    kwargs = _minimal_inputs()
    usf = build_usf_object(usf_version="1.0", **kwargs)
    assert "usf_version" in usf
    assert "logic_outputs" in usf
    assert "raw_metrics" in usf
    assert "structural_state" not in usf
    assert "fingerprint" not in usf


def test_generate_usf_with_interpretation_metrics_succeeds():
    kwargs = _minimal_inputs()
    kwargs["interpretation_metrics"] = {
        "structural_state": "distributed_balanced",
        "dominant_area_id": 0,
        "dominance_strength": 0.08,
        "entropy_state": "stable",
        "tension_state": "normal",
        "propagation_state": "minimal_spread",
        "active_events": [],
        "interpretation_flags": [],
        "event_summary": {},
        "interpretation_diagnostics": {},
    }
    usf = generate_usf(usf_version="1.0", **kwargs)
    assert usf["structural_state"] == "distributed_balanced"
    assert "compatibility" in usf
    assert usf["compatibility"]["legacy_logic_outputs_present"] is True
