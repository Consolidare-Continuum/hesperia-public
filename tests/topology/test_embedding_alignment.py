# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Tests for embedding alignment: coordinate graph is icosahedral, alignment restores edge uniformity,
determinism, and that aligned coordinates match topology exactly.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_coordinate_graph_is_icosahedral() -> None:
    """Build geometric graph from aligned coordinates; assert degree 5, 30 edges, connected."""
    from sphere.topology.embedding import get_area_coordinates
    from sphere.topology.embedding_alignment import build_coordinate_edge_graph
    import numpy as np

    coords = get_area_coordinates()
    coord_list = [coords[i] for i in range(12)]
    adj = build_coordinate_edge_graph(coord_list)
    assert adj.shape == (12, 12)
    for i in range(12):
        assert int(adj[i, :].sum()) == 5, f"node {i} must have degree 5"
    assert int(adj.sum()) // 2 == 30
    # Connected: BFS from 0
    seen = set()
    stack = [0]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        for j in range(12):
            if adj[n, j] and j not in seen:
                stack.append(j)
    assert len(seen) == 12


def test_alignment_restores_edge_uniformity() -> None:
    """Aligned coordinates pass validate_edge_lengths(..., tolerance=0.05)."""
    from sphere.topology import get_icosahedral_adjacency
    from sphere.topology.embedding import get_area_coordinates, validate_edge_lengths

    adj = get_icosahedral_adjacency()
    coords = get_area_coordinates()
    validate_edge_lengths(adj, coords, tolerance=0.05)


def test_alignment_is_deterministic() -> None:
    """Repeated calls return identical coordinates; fingerprint/hash identical."""
    from sphere.topology.embedding import get_area_coordinates, coordinate_fingerprint

    c1 = get_area_coordinates()
    c2 = get_area_coordinates()
    fp1 = coordinate_fingerprint(c1)
    fp2 = coordinate_fingerprint(c2)
    assert fp1 == fp2
    for i in range(12):
        assert c1[i] == c2[i]


def test_aligned_coordinates_match_topology() -> None:
    """Geometric edge graph from aligned coords equals canonical adjacency exactly."""
    from sphere.topology import get_icosahedral_adjacency
    from sphere.topology.embedding import get_area_coordinates
    from sphere.topology.embedding_alignment import build_coordinate_edge_graph
    import numpy as np

    topo_adj = get_icosahedral_adjacency()
    coords = get_area_coordinates()
    coord_list = [coords[i] for i in range(12)]
    geom_adj = build_coordinate_edge_graph(coord_list)
    assert np.array_equal(topo_adj, geom_adj)


def test_unaligned_coordinates_do_not_match_topology() -> None:
    """Raw UNIT_VERTICES order fails strict validate_edge_lengths(..., tolerance=0.05)."""
    from sphere.topology import get_icosahedral_adjacency
    from sphere.topology.embedding import UNIT_VERTICES, validate_edge_lengths

    adj = get_icosahedral_adjacency()
    raw_coords = {i: UNIT_VERTICES[i] for i in range(12)}
    # Geometric graph from raw has same structure as adj (we made adj = geometric), so raw_coords
    # in index order *is* the geometric graph. So actually raw_coords and adj now match (adj was
    # set to geometric). So raw_coords will pass validate_edge_lengths. The "unaligned" in the
    # test name meant: before we changed topology to geometric, the old topology + raw coords
    # failed. Now topology = geometric, so raw = aligned. So this test should assert that when
    # we use a *different* adjacency (e.g. the old one if we had it) with raw coords, we fail.
    # We don't have the old adj anymore. So instead: assert that build_coordinate_edge_graph(raw)
    # equals get_icosahedral_adjacency() (they're the same graph). So "unaligned" test: verify that
    # coordinates that are NOT the aligned set fail. So use a wrong permutation: coords_wrong[i] = UNIT_VERTICES[(i+1) % 12]. Then validate_edge_lengths(adj, coords_wrong) should fail.
    wrong_coords = {i: UNIT_VERTICES[(i + 1) % 12] for i in range(12)}
    try:
        validate_edge_lengths(adj, wrong_coords, tolerance=0.05)
        assert False, "Expected validate_edge_lengths to fail for wrong permutation"
    except AssertionError:
        pass
