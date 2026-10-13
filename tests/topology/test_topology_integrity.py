# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Topology integrity test suite: symmetry, degree, edge count, connectivity, diameter, fingerprint.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_symmetry() -> None:
    """Loaded adjacency matrix is symmetric."""
    from sphere.topology import load_area_adjacency

    adj = load_area_adjacency()
    assert np.array_equal(adj, adj.T), "adjacency must be symmetric"


def test_degree_regular() -> None:
    """Every node has degree 5."""
    from sphere.topology import load_area_adjacency, ICOSAHEDRAL_DEGREE

    adj = load_area_adjacency()
    for i in range(12):
        assert int(adj[i, :].sum()) == ICOSAHEDRAL_DEGREE, f"node {i} must have degree 5"


def test_edge_count() -> None:
    """Total edges == 30."""
    from sphere.topology import load_area_adjacency, ICOSAHEDRAL_EDGES

    adj = load_area_adjacency()
    assert int(adj.sum()) // 2 == ICOSAHEDRAL_EDGES, "must have 30 edges"


def test_connected_component() -> None:
    """Graph is a single connected component."""
    from sphere.topology import build_topology_graph

    graph = build_topology_graph()
    neighbors = graph["neighbors"]
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
    assert len(seen) == 12, "graph must be connected (12 nodes reachable)"


def test_diameter() -> None:
    """Icosahedron graph diameter is 3."""
    from sphere.topology import load_area_adjacency
    from sphere.topology.metrics import graph_diameter

    adj = load_area_adjacency()
    d = graph_diameter(adj)
    assert d == 3, f"icosahedron diameter must be 3, got {d}"


def test_fingerprint_stable() -> None:
    """Topology fingerprint is deterministic (same matrix → same hash)."""
    from sphere.topology import get_icosahedral_adjacency, topology_fingerprint

    adj = get_icosahedral_adjacency()
    fp1 = topology_fingerprint(adj)
    fp2 = topology_fingerprint(adj.tolist())
    assert fp1 == fp2, "fingerprint must be stable for same topology"
    assert len(fp1) == 64, "SHA256 hex digest must be 64 chars"
    assert all(c in "0123456789abcdef" for c in fp1), "fingerprint must be hex"


def test_build_topology_graph_includes_fingerprint() -> None:
    """build_topology_graph returns nodes, edges, degree, fingerprint, coordinate_fingerprint."""
    from sphere.topology import build_topology_graph, ICOSAHEDRAL_EDGES, ICOSAHEDRAL_DEGREE

    graph = build_topology_graph()
    assert graph["nodes"] == 12
    assert graph["areas"] == 12
    assert graph["edges"] == ICOSAHEDRAL_EDGES
    assert graph["degree"] == ICOSAHEDRAL_DEGREE
    assert "fingerprint" in graph
    assert len(graph["fingerprint"]) == 64
    assert "coordinate_fingerprint" in graph
    assert len(graph["coordinate_fingerprint"]) == 64


def test_build_topology_graph_includes_coordinates() -> None:
    """build_topology_graph returns coordinates (unit-sphere embedding)."""
    from sphere.topology import build_topology_graph

    graph = build_topology_graph()
    assert "coordinates" in graph
    coords = graph["coordinates"]
    assert len(coords) == 12
    for i in range(12):
        x, y, z = coords[i]
        assert abs((x * x + y * y + z * z) ** 0.5 - 1.0) < 1e-9
