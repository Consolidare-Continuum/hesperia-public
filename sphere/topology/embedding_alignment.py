# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Deterministic alignment of icosahedral 3-D embedding to canonical topology graph.
Computes graph isomorphism between topology adjacency and geometric edge graph,
then selects a canonical mapping so that A1..A12 coordinates match the topology.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from sphere.topology.embedding import angular_distance

NUM_NODES = 12
NUM_EDGES = 30
DEGREE = 5


def build_coordinate_edge_graph(
    coords: dict[int, tuple[float, float, float]] | list[tuple[float, float, float]],
    tolerance: float = 1e-6,
) -> np.ndarray:
    """
    Build the icosahedral edge graph from coordinates by:
    1. Computing all pairwise angular distances
    2. Finding the minimum nonzero distance (canonical edge length)
    3. Connecting pairs whose angular distance is within tolerance of that minimum.

    Returns 12×12 symmetric adjacency matrix (binary).
    Validates: 12 nodes, 30 edges, degree 5 per node.
    """
    if isinstance(coords, dict):
        coord_list = [coords[i] for i in range(len(coords))]
    else:
        coord_list = list(coords)
    n = len(coord_list)
    if n != NUM_NODES:
        raise ValueError(f"coords must have {NUM_NODES} nodes, got {n}")

    # All pairwise angular distances (i < j)
    distances: list[tuple[float, int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            d = angular_distance(coord_list[i], coord_list[j])
            distances.append((d, i, j))
    distances.sort(key=lambda x: x[0])

    # Minimum nonzero distance = canonical edge length
    d_min = None
    for d, i, j in distances:
        if d > 1e-12:  # nonzero
            d_min = d
            break
    if d_min is None:
        raise ValueError("All pairwise distances are zero")

    # Build adjacency: edge (i,j) iff abs(d(i,j) - d_min) <= tolerance
    adj = np.zeros((n, n), dtype=np.int64)
    for d, i, j in distances:
        if abs(d - d_min) <= tolerance:
            adj[i, j] = 1
            adj[j, i] = 1

    # Validation
    total_edges = int(adj.sum()) // 2
    if total_edges != NUM_EDGES:
        raise ValueError(f"Coordinate edge graph must have {NUM_EDGES} edges, got {total_edges}")
    for i in range(n):
        deg = int(adj[i, :].sum())
        if deg != DEGREE:
            raise ValueError(f"Coordinate graph node {i} must have degree {DEGREE}, got {deg}")

    return adj


def _adj_to_networkx_graph(adj: np.ndarray):
    """Build networkx Graph from 12×12 adjacency (for isomorphism)."""
    import networkx as nx
    G = nx.Graph()
    n = adj.shape[0]
    for i in range(n):
        G.add_node(i)
    for i in range(n):
        for j in range(i + 1, n):
            if adj[i, j]:
                G.add_edge(i, j)
    return G


def _get_all_isomorphisms(G_topology, G_coords):
    """Return list of dict mappings: topology_node -> coord_node."""
    import networkx as nx
    # Isomorphism f: G_topology -> G_coords so f(topology_node) = coord_node.
    try:
        # networkx 3.x: vf2pp_all_isomorphisms(G1, G2) yields dict G1->G2
        it = nx.vf2pp_all_isomorphisms(G_topology, G_coords)
        return [dict(m) for m in it]
    except AttributeError:
        pass
    # Fallback: GraphMatcher gives one mapping
    GM = nx.isomorphism.GraphMatcher(G_topology, G_coords)
    if not GM.is_isomorphic():
        return []
    return [dict(GM.mapping)]


def choose_canonical_mapping(
    mappings: list[dict[int, int]],
    coords: list[tuple[float, float, float]],
) -> dict[int, int]:
    """
    From multiple valid isomorphisms (topology_index -> coord_index), choose one
    deterministically: the mapping whose reordered coordinate list serializes
    to the lexicographically smallest JSON string.
    """
    if not mappings:
        raise ValueError("No mappings provided")
    best: dict[int, int] | None = None
    best_key: str | None = None
    for mapping in mappings:
        # mapping: topology_i -> coord_j. Reordered: coords_for_topology[i] = coords[mapping[i]]
        reordered = [list(coords[mapping[i]]) for i in range(12)]
        key = json.dumps(reordered, separators=(",", ":"))
        if best_key is None or key < best_key:
            best = mapping
            best_key = key
    assert best is not None
    return best


def find_embedding_permutation(
    topology_adj: np.ndarray,
    coords: dict[int, tuple[float, float, float]] | list[tuple[float, float, float]],
    tolerance: float = 1e-6,
) -> dict[int, int]:
    """
    Return deterministic mapping: topology_index -> coordinate_index,
    so that when we assign coord[mapping[i]] to area i, the resulting
    geometric edge graph (from coordinates in area order) equals topology_adj.

    Uses graph isomorphism between topology and coordinate-edge graph,
    then choose_canonical_mapping for deterministic tie-breaking.
    """
    import networkx as nx

    topology_adj = np.asarray(topology_adj)
    if topology_adj.shape != (NUM_NODES, NUM_NODES):
        raise ValueError(f"topology_adj must be {NUM_NODES}×{NUM_NODES}")

    if isinstance(coords, dict):
        coord_list = [coords[i] for i in range(NUM_NODES)]
    else:
        coord_list = list(coords)
    if len(coord_list) != NUM_NODES:
        raise ValueError(f"coords must have {NUM_NODES} entries")

    # Geometric edge graph from raw coordinate order (vertex 0..11)
    coord_adj = build_coordinate_edge_graph(coord_list, tolerance=tolerance)

    G_topology = _adj_to_networkx_graph(topology_adj)
    G_coords = _adj_to_networkx_graph(coord_adj)

    if not nx.is_isomorphic(G_topology, G_coords):
        raise ValueError("Topology and coordinate graphs are not isomorphic")

    # Get all isomorphisms: topology node -> coord node
    isos = _get_all_isomorphisms(G_topology, G_coords)
    if not isos:
        raise ValueError("No isomorphism found between topology and coordinate graph")

    # Deterministic choice: lexicographically smallest reordered coordinates
    return choose_canonical_mapping(isos, coord_list)
