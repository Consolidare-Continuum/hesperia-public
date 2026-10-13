# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Tests for icosahedral 3-D embedding: unit sphere, vertex count, edge lengths, determinism.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_unit_sphere() -> None:
    """All coordinates lie on unit sphere (||coord|| ≈ 1)."""
    from sphere.topology.embedding import get_area_coordinates

    coords = get_area_coordinates()
    for i, (x, y, z) in coords.items():
        r = math.sqrt(x * x + y * y + z * z)
        assert abs(r - 1.0) < 1e-9, f"Area {i} has ||coord||={r}, expected 1.0"


def test_vertex_count() -> None:
    """Exactly 12 vertices (areas A1–A12)."""
    from sphere.topology.embedding import get_area_coordinates, UNIT_VERTICES

    assert len(UNIT_VERTICES) == 12
    coords = get_area_coordinates()
    assert len(coords) == 12
    assert list(coords.keys()) == list(range(12))


def test_edge_length_consistency() -> None:
    """Aligned embedding yields near-equal angular distances for all graph edges (tolerance=0.05)."""
    from sphere.topology import get_icosahedral_adjacency
    from sphere.topology.embedding import get_area_coordinates, validate_edge_lengths

    adj = get_icosahedral_adjacency()
    coords = get_area_coordinates()
    validate_edge_lengths(adj, coords, tolerance=0.05)


def test_coordinate_determinism() -> None:
    """Hash of coordinates is stable across calls (deterministic embedding)."""
    from sphere.topology.embedding import get_area_coordinates

    coords1 = get_area_coordinates()
    coords2 = get_area_coordinates()
    # Serialize to canonical form for hashing
    def canonical(coords: dict) -> bytes:
        data = {str(k): list(v) for k, v in sorted(coords.items())}
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()

    h1 = hashlib.sha256(canonical(coords1)).hexdigest()
    h2 = hashlib.sha256(canonical(coords2)).hexdigest()
    assert h1 == h2, "Coordinates must be deterministic (same hash)"


def test_angular_distance_bounds() -> None:
    """angular_distance returns 0 for same point, π for antipodal (clamped)."""
    from sphere.topology.embedding import angular_distance, get_area_coordinates

    coords = get_area_coordinates()
    p0 = coords[0]
    assert abs(angular_distance(p0, p0)) < 1e-9
    # Distance to self is 0; to another point in (0, π)
    p1 = coords[1]
    d = angular_distance(p0, p1)
    assert 0 < d < math.pi + 0.01


def test_geodesic_distance() -> None:
    """geodesic_distance = radius * angular_distance."""
    from sphere.topology.embedding import angular_distance, geodesic_distance, get_area_coordinates

    coords = get_area_coordinates()
    p0, p1 = coords[0], coords[1]
    r = 2.0
    assert abs(geodesic_distance(p0, p1, radius=r) - r * angular_distance(p0, p1)) < 1e-9
