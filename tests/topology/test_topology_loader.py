# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Tests for topology loader (load_area_adjacency, load_family_area_mapping, build_topology_graph).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_load_all_returns_three_artifacts() -> None:
    """load_all returns adjacency_matrix, family_to_area, topology_graph."""
    from sphere.topology import load_all
    adj, f2a, graph = load_all()
    assert adj.shape == (12, 12)
    assert len(f2a) == 288
    assert graph["areas"] == 12
    assert "neighbors" in graph


def test_build_topology_graph_icosahedral() -> None:
    """Icosahedral topology: area 0 (A1) has 5 neighbors (geometric icosahedron)."""
    from sphere.topology import build_topology_graph, ICOSAHEDRAL_DEGREE, ICOSAHEDRAL_EDGES
    graph = build_topology_graph()
    assert set(graph["neighbors"][0]) == {1, 5, 7, 10, 11}
    assert graph["edges"] == ICOSAHEDRAL_EDGES
    for i in range(12):
        assert len(graph["neighbors"][i]) == ICOSAHEDRAL_DEGREE, f"area {i} must have degree 5"
