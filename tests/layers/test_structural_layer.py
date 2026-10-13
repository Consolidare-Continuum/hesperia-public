# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Unit tests for structural layer (L3).
Verifies shadow divergence, L1/L2 consumption.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.layers.layer_3 import compute_L3


def _l1_stub() -> dict:
    return {
        "DOMINANT_FAMILY_ID": 0,
        "DOMINANT_AREA_ID": 0,
        "DOMINANCE_RATIO": 0.4,
        "COVERAGE_RATIO": 0.5,
        "UNIQUE_FAMILIES_HIT": 3,
        "AREA_SPREAD": 0.2,
        "NORMALIZED_FAMILY_ENTROPY": 0.3,
        "GINI_COEFFICIENT": 0.5,
        "MEAN_ALTITUDE_GLOBAL": 0.1,
        "MEAN_ALTITUDE_DOMINANT": 0.2,
        "FAMILY_HIT_VECTOR_L1": 0.1,
    }


def _l2_stub() -> dict:
    return {
        "VISITED_IDS": [0, 1, 2],
        "TOTAL_REACHABLE_NODES": 3,
        "TRAVERSAL_DEPTH_REACHED": 2,
        "MAX_TRAVERSAL_DISTANCE": 2,
        "CROSS_AREA_RATIO": 0.0,
        "LOOP_DENSITY": 0.0,
        "EDGE_UTILIZATION_RATIO": 0.1,
    }


def test_l3_structural_output_keys() -> None:
    """L3 result includes SHADOW_ENABLED and delta-style keys."""
    l1 = _l1_stub()
    l2 = _l2_stub()
    hits = [1] * 3 + [0] * 285
    result = compute_L3(l1, l2, hits, l1, l2, hits, F=288, A=12)
    assert "SHADOW_ENABLED" in result
    assert "COVERAGE_RATIO_DELTA" in result or "ENTROPY_DELTA" in result


def test_l3_deterministic() -> None:
    """Same inputs produce same L3 output."""
    l1 = _l1_stub()
    l1["DOMINANT_FAMILY_ID"] = 10
    l2 = _l2_stub()
    l2["VISITED_IDS"] = [10, 11]
    l2["TOTAL_REACHABLE_NODES"] = 2
    hits = [0] * 288
    hits[10] = 5
    hits[11] = 2
    a = compute_L3(l1, l2, hits, l1, l2, hits, F=288, A=12)
    b = compute_L3(l1, l2, hits, l1, l2, hits, F=288, A=12)
    assert a == b
