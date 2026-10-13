# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Topology validation: graph connectivity — no isolated nodes, graph structure valid.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_graph_no_isolated_nodes() -> None:
    """Every area has exactly 5 neighbors (icosahedral)."""
    from sphere.topology import build_topology_graph, ICOSAHEDRAL_DEGREE
    graph = build_topology_graph()
    neighbors = graph.get("neighbors", {})
    assert len(neighbors) == 12
    for area in range(12):
        adj = neighbors.get(area, [])
        assert len(adj) == ICOSAHEDRAL_DEGREE, f"Area {area} must have degree {ICOSAHEDRAL_DEGREE}"


def test_graph_connectivity() -> None:
    """Graph is connected: from node 0 we can reach all 12 nodes (BFS)."""
    from sphere.topology import build_topology_graph
    graph = build_topology_graph()
    neighbors = graph.get("neighbors", {})
    seen = set()
    stack = [0]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        for j in neighbors.get(n, []):
            if j not in seen:
                stack.append(j)
    assert len(seen) == 12, f"Graph not connected: reached {len(seen)}/12 nodes"
