# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Unit tests for dynamism layer (sphere.dynamism).
Verifies trajectory, transition matrix, curvature, jump_rate, stability_index.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_dynamism_trajectory_and_compressed() -> None:
    """compute_dynamism returns trajectory with raw and compressed."""
    from sphere.dynamism import compute_dynamism
    from sphere.topology import load_area_adjacency
    adj = load_area_adjacency()
    area_seq = [2, 2, 5, 4, 4, 1]
    out = compute_dynamism([0] * 6, area_seq, adj)
    assert "trajectory" in out
    assert out["trajectory"]["raw"] == area_seq
    assert out["trajectory"]["compressed"] == [2, 5, 4, 1]


def test_dynamism_transition_matrix_shape() -> None:
    """Transition matrix is 12x12 (list of lists)."""
    from sphere.dynamism import compute_dynamism
    from sphere.topology import load_area_adjacency
    adj = load_area_adjacency()
    out = compute_dynamism([0] * 4, [0, 1, 2, 1], adj)
    assert len(out["transition_matrix"]) == 12
    assert all(len(row) == 12 for row in out["transition_matrix"])


def test_dynamism_curvature_bounds() -> None:
    """Curvature in [0, 2]."""
    from sphere.dynamism import compute_dynamism
    from sphere.topology import load_area_adjacency
    adj = load_area_adjacency()
    out = compute_dynamism([0] * 5, [0, 1, 5, 2, 0], adj)
    assert 0 <= out["curvature"] <= 2.0


def test_dynamism_jump_rate_structure() -> None:
    """jump_rate has jump_count and jump_rate keys."""
    from sphere.dynamism import compute_dynamism
    from sphere.topology import load_area_adjacency
    adj = load_area_adjacency()
    out = compute_dynamism([0] * 3, [0, 5, 0], adj)
    assert "jump_count" in out["jump_rate"]
    assert "jump_rate" in out["jump_rate"]
    assert 0 <= out["jump_rate"]["jump_rate"] <= 1.0


def test_dynamism_stability_index_bounds() -> None:
    """stability_index in [0, 1]."""
    from sphere.dynamism import compute_dynamism
    from sphere.topology import load_area_adjacency
    adj = load_area_adjacency()
    out = compute_dynamism([0] * 4, [1, 1, 1, 1], adj)
    assert 0 <= out["stability_index"] <= 1.0
