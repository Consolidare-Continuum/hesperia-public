# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Tests for area adjacency matrix (12x12, symmetric, diagonal 0).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_adjacency_matrix_shape() -> None:
    """Loaded adjacency matrix is 12x12."""
    from sphere.topology import load_area_adjacency
    matrix = load_area_adjacency()
    assert matrix.shape == (12, 12)


def test_adjacency_matrix_symmetric() -> None:
    """Adjacency matrix is symmetric."""
    from sphere.topology import load_area_adjacency
    import numpy as np
    matrix = load_area_adjacency()
    assert np.array_equal(matrix, matrix.T)


def test_adjacency_matrix_diagonal_zero() -> None:
    """Diagonal elements are 0."""
    from sphere.topology import load_area_adjacency
    matrix = load_area_adjacency()
    for i in range(12):
        assert matrix[i, i] == 0


def test_adjacency_matrix_binary() -> None:
    """All entries are 0 or 1."""
    from sphere.topology import load_area_adjacency
    import numpy as np
    matrix = load_area_adjacency()
    assert np.all((matrix == 0) | (matrix == 1))


def test_icosahedral_degree_five() -> None:
    """Icosahedral rule: every node has degree 5."""
    from sphere.topology import load_area_adjacency, ICOSAHEDRAL_DEGREE
    matrix = load_area_adjacency()
    for i in range(12):
        assert matrix[i, :].sum() == ICOSAHEDRAL_DEGREE, f"node {i} must have degree {ICOSAHEDRAL_DEGREE}"


def test_icosahedral_edge_count() -> None:
    """Icosahedral rule: total edges == 30 (symmetric, so sum/2)."""
    from sphere.topology import load_area_adjacency, ICOSAHEDRAL_EDGES
    matrix = load_area_adjacency()
    total_edges = int(matrix.sum()) // 2
    assert total_edges == ICOSAHEDRAL_EDGES, f"expected {ICOSAHEDRAL_EDGES} edges, got {total_edges}"


def test_validate_icosahedral_rejects_ring() -> None:
    """validate_icosahedral raises when matrix has degree != 5 (e.g. ring)."""
    import numpy as np
    from sphere.topology import validate_icosahedral
    ring = np.zeros((12, 12), dtype=np.int64)
    for i in range(12):
        ring[i, (i - 1) % 12] = 1
        ring[i, (i + 1) % 12] = 1
    try:
        validate_icosahedral(ring)
        assert False, "expected ValueError for ring (degree 2)"
    except ValueError as e:
        assert "degree" in str(e).lower() or "5" in str(e)
