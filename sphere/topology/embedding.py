# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Deterministic spherical embedding of the 12-node icosahedral topology.
Each area (A1–A12) has fixed 3-D coordinates on the unit sphere for geometric metrics
(angular distance, clustering) while keeping the graph topology unchanged.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

import numpy as np

# Golden ratio φ = (1 + √5) / 2
PHI = (1.0 + math.sqrt(5.0)) / 2.0

# Standard icosahedron vertices (before normalization). Order defines A1→v0, ..., A12→v11.
ICOSAHEDRON_VERTICES_RAW: tuple[tuple[float, float, float], ...] = (
    (-1.0, PHI, 0.0),
    (1.0, PHI, 0.0),
    (-1.0, -PHI, 0.0),
    (1.0, -PHI, 0.0),
    (0.0, -1.0, PHI),
    (0.0, 1.0, PHI),
    (0.0, -1.0, -PHI),
    (0.0, 1.0, -PHI),
    (PHI, 0.0, -1.0),
    (PHI, 0.0, 1.0),
    (-PHI, 0.0, -1.0),
    (-PHI, 0.0, 1.0),
)

def normalize_vertices(
    vertices: tuple[tuple[float, float, float], ...] | list[tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    """Normalize each (x, y, z) to unit sphere. Returns list of (x/r, y/r, z/r)."""
    normed: list[tuple[float, float, float]] = []
    for x, y, z in vertices:
        r = math.sqrt(x * x + y * y + z * z)
        normed.append((x / r, y / r, z / r))
    return normed


# Normalized vertices on unit sphere (computed at import)
UNIT_VERTICES: tuple[tuple[float, float, float], ...] = tuple(
    normalize_vertices(ICOSAHEDRON_VERTICES_RAW)
)

# Cache aligned coordinates for canonical topology (lazy, set by get_aligned_area_coordinates)
_ALIGNED_COORDINATES_CACHE: dict[int, dict[int, tuple[float, float, float]]] = {}


def get_aligned_area_coordinates(
    adj: np.ndarray | None = None,
) -> dict[int, tuple[float, float, float]]:
    """
    Return canonical aligned coordinates in area order A1..A12 so that the
    geometric edge graph of the returned coordinates equals the topology graph.
    Uses deterministic graph isomorphism + lexicographic tie-break.
    """
    from sphere.topology.embedding_alignment import find_embedding_permutation
    from sphere.topology.topology_loader import get_icosahedral_adjacency

    if adj is None:
        adj = get_icosahedral_adjacency()
    adj = np.asarray(adj)
    # Use hash of adj for cache key (canonical adj is fixed)
    key = hash(adj.tobytes())
    if key in _ALIGNED_COORDINATES_CACHE:
        return _ALIGNED_COORDINATES_CACHE[key]
    raw_list = list(UNIT_VERTICES)
    mapping = find_embedding_permutation(adj, raw_list)
    aligned = {i: raw_list[mapping[i]] for i in range(12)}
    _ALIGNED_COORDINATES_CACHE[key] = aligned
    return aligned


def get_area_coordinates() -> dict[int, tuple[float, float, float]]:
    """
    Aligned coordinates in area order A1..A12 (topology-consistent).
    Same as get_aligned_area_coordinates() for the canonical icosahedral adjacency.
    """
    from sphere.topology.topology_loader import get_icosahedral_adjacency
    return get_aligned_area_coordinates(get_icosahedral_adjacency())


def angular_distance(
    p1: tuple[float, float, float] | list[float],
    p2: tuple[float, float, float] | list[float],
) -> float:
    """
    Angular distance between two points on unit sphere (radians).
    Uses dot product clamped to [-1, 1] then acos.
    """
    dot = sum(a * b for a, b in zip(p1, p2))
    dot = max(-1.0, min(1.0, dot))
    return math.acos(dot)


def geodesic_distance(
    p1: tuple[float, float, float] | list[float],
    p2: tuple[float, float, float] | list[float],
    radius: float = 1.0,
) -> float:
    """Geodesic distance on sphere of given radius (radius * angular_distance)."""
    return radius * angular_distance(p1, p2)


def coordinate_fingerprint(coords: dict[int, tuple[float, float, float]]) -> str:
    """
    SHA256 of aligned coordinates serialized deterministically (area 0..11 order).
    Protects the embedding layer against drift.
    """
    ordered = [list(coords[i]) for i in range(12)]
    data = json.dumps(ordered, separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(data.encode()).hexdigest()


def validate_edge_lengths(
    adj: np.ndarray | list[list[Any]],
    coords: dict[int, tuple[float, float, float]],
    *,
    tolerance: float = 0.05,
) -> None:
    """
    Check that all graph edges correspond to nearly equal angular distances
    (icosahedral edges have equal chord length). Raises AssertionError if
    max(angular_distances) - min(angular_distances) >= tolerance.
    """
    a = np.asarray(adj)
    lengths: list[float] = []
    for i in range(12):
        for j in range(i + 1, 12):
            if a[i, j]:
                lengths.append(angular_distance(coords[i], coords[j]))
    if not lengths:
        return
    diff = max(lengths) - min(lengths)
    assert diff < tolerance, (
        f"Edge angular lengths should be nearly equal (diff < {tolerance}), got diff={diff}"
    )


def validate_embedding_matches_topology(
    adj: np.ndarray | list[list[Any]],
    coords: dict[int, tuple[float, float, float]],
    *,
    tolerance: float = 0.05,
    margin: float = 0.1,
) -> None:
    """
    1. All graph edges have near-equal angular length (within tolerance).
    2. All non-edges are strictly longer than edge_length + margin.
    Raises AssertionError on violation.
    """
    a = np.asarray(adj)
    edge_lengths: list[float] = []
    non_edge_lengths: list[float] = []
    for i in range(12):
        for j in range(i + 1, 12):
            d = angular_distance(coords[i], coords[j])
            if a[i, j]:
                edge_lengths.append(d)
            else:
                non_edge_lengths.append(d)
    if not edge_lengths:
        return
    d_min = min(edge_lengths)
    d_max_edge = max(edge_lengths)
    assert d_max_edge - d_min < tolerance, (
        f"Edge length spread must be < {tolerance}, got {d_max_edge - d_min}"
    )
    edge_upper = d_max_edge + margin
    for d in non_edge_lengths:
        assert d > edge_upper, (
            f"Non-edge angular distance {d} must be > edge_upper {edge_upper}"
        )
