# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
USF serialization determinism: same USF -> same JSON.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_usf_serialization_deterministic() -> None:
    """Serializing the same USF twice yields identical JSON."""
    from sphere.usf import generate_usf, serialize_usf_to_json
    raw = {"area_vector": [0.1] * 12, "family_counts": [0.0] * 288, "family_peaks": [], "dominant_area": 0, "dominant_family": 0, "entropy": 0.0, "tension": 0.0, "loopability": 0.0, "coverage": 0.0}
    dyn = {"trajectory": {}, "transition_matrix": [[0] * 12] * 12, "curvature": 0.0, "jump_rate": 0.0, "stability_index": 0.0}
    prop = {"propagated_area_vector": [0.0] * 12, "propagated_family_counts": [0.0] * 288}
    logic = {"triggered_rules": [], "logic_flags": [], "structural_diagnostics": []}
    prov = {"created_at": "2025-01-01T00:00:00Z", "pipeline_version": "v1", "input_hash": "abc", "deterministic": True}
    usf = generate_usf("d", {}, raw, dyn, prop, logic, prov)
    json1 = serialize_usf_to_json(usf)
    json2 = serialize_usf_to_json(usf)
    assert json1 == json2
