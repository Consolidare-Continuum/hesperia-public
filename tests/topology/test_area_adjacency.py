# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Topology validation: 12x12 adjacency matrix, symmetry, diagonal zero, binary.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_adjacency_12x12() -> None:
    """Adjacency matrix is 12x12."""
    from sphere.topology import load_area_adjacency
    matrix = load_area_adjacency()
    assert matrix.shape == (12, 12)


def test_adjacency_symmetric() -> None:
    """Adjacency matrix is symmetric."""
    from sphere.topology import load_area_adjacency
    import numpy as np
    matrix = load_area_adjacency()
    assert np.array_equal(matrix, matrix.T)


def test_adjacency_diagonal_zero() -> None:
    """Diagonal elements are 0."""
    from sphere.topology import load_area_adjacency
    matrix = load_area_adjacency()
    for i in range(12):
        assert matrix[i, i] == 0


def test_adjacency_no_isolated_nodes() -> None:
    """No isolated nodes: every row has at least one neighbor (off-diagonal)."""
    from sphere.topology import load_area_adjacency
    matrix = load_area_adjacency()
    for i in range(12):
        row_sum = sum(matrix[i, j] for j in range(12) if j != i)
        assert row_sum >= 1, f"Area {i} has no neighbors"
