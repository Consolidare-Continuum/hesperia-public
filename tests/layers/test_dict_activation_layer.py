# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Unit tests for dict activation / traversal layer (L2).
Verifies VISITED_IDS, traversal depth, adjacency use.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.contracts.layer_contract import LayerInput
from core.layers.layer_2 import compute_L2, build_canonical_stub_adjacency, run


def test_l2_visited_ids_present() -> None:
    """L2 result includes VISITED_IDS and TOTAL_REACHABLE_NODES."""
    F, A = 288, 12
    adjacency = build_canonical_stub_adjacency(F, A)
    hits = [0] * F
    hits[0] = 5
    l1 = {"DOMINANT_FAMILY_ID": 0, "DOMINANT_AREA_ID": 0}
    result = compute_L2(l1, hits, adjacency=adjacency, F=F, A=A)
    assert "VISITED_IDS" in result
    assert "TOTAL_REACHABLE_NODES" in result
    assert isinstance(result["VISITED_IDS"], (list, set)) or hasattr(result["VISITED_IDS"], "__iter__")


def test_l2_adjacency_shape() -> None:
    """Stub adjacency has F nodes."""
    adj = build_canonical_stub_adjacency(288, 12)
    assert len(adj) == 288


def test_l2_run_contract() -> None:
    """L2 run() returns LayerOutput with layer_id=2."""
    meta = {
        "F": 288, "A": 12, "eps": 1e-9, "MAX_ALLOWED_DEPTH": 8,
        "hits": [1] + [0] * 287,
        "layers": {
            1: {"DOMINANT_FAMILY_ID": 0, "DOMINANT_AREA_ID": 0},
        },
    }
    inp = LayerInput(text="test", tokens=["test"], metadata=meta)
    out = run(inp)
    assert out.layer_id == 2
    assert "VISITED_IDS" in out.result
