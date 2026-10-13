# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Unit tests for propagation-related outputs.
Verifies propagated_area_vector and propagated_family_counts shape when present (e.g. from USF).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_propagated_area_vector_length() -> None:
    """Propagated area vector from USF/pipeline has length 12."""
    from sphere.usf import generate_usf
    raw = {
        "area_vector": [0.1] * 12,
        "family_counts": [0] * 288,
        "family_peaks": [],
        "dominant_area": 0,
        "dominant_family": 0,
        "entropy": 0.0,
        "tension": 0.0,
        "loopability": 0.0,
        "coverage": 0.0,
    }
    dyn = {"trajectory": {}, "transition_matrix": [[0] * 12 for _ in range(12)], "curvature": 0.0, "jump_rate": 0.0, "stability_index": 0.0}
    prop = {"propagated_area_vector": [0.0] * 12, "propagated_family_counts": [0.0] * 288}
    logic = {"triggered_rules": [], "logic_flags": [], "structural_diagnostics": []}
    prov = {"created_at": "", "pipeline_version": "v1", "input_hash": "", "deterministic": True}
    usf = generate_usf("doc1", {}, raw, dyn, prop, logic, prov)
    assert len(usf["propagation_metrics"]["propagated_area_vector"]) == 12
    assert len(usf["propagation_metrics"]["propagated_family_counts"]) == 288


def test_propagated_family_counts_length() -> None:
    """Propagated family counts length is 288."""
    from sphere.usf import generate_usf
    raw = {"area_vector": [0.0] * 12, "family_counts": [0] * 288, "family_peaks": [], "dominant_area": 0, "dominant_family": 0, "entropy": 0.0, "tension": 0.0, "loopability": 0.0, "coverage": 0.0}
    dyn = {"trajectory": {}, "transition_matrix": [[0] * 12] * 12, "curvature": 0.0, "jump_rate": 0.0, "stability_index": 0.0}
    prop = {"propagated_area_vector": [0.0] * 12, "propagated_family_counts": [0.0] * 288}
    logic = {"triggered_rules": [], "logic_flags": [], "structural_diagnostics": []}
    prov = {"created_at": "", "pipeline_version": "v1", "input_hash": "", "deterministic": True}
    usf = generate_usf("doc1", {}, raw, dyn, prop, logic, prov)
    assert len(usf["propagation_metrics"]["propagated_family_counts"]) == 288
