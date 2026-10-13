# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Mass may only diffuse to adjacent areas. Non-adjacent targets unchanged in single-step.
"""

from __future__ import annotations

import numpy as np
import pytest

from sphere.propagation.diffusion import build_propagation_matrix, diffuse_once
from core.math.diffusion import diffuse_step


def test_propagation_matrix_zero_where_no_adjacency():
    # Only neighbors get non-zero row entries
    adj = np.zeros((12, 12), dtype=np.float64)
    adj[0, 1] = 1
    adj[0, 11] = 1
    W = build_propagation_matrix(adj)
    assert W[0, 1] > 0
    assert W[0, 11] > 0
    assert W[0, 2] == 0
    assert W[0, 5] == 0
    assert abs(W[0, 1] + W[0, 11] - 1.0) < 1e-9


def test_mass_only_flows_to_neighbors():
    adj = np.zeros((12, 12), dtype=np.float64)
    for i in range(12):
        adj[i, (i - 1) % 12] = 1
        adj[i, (i + 1) % 12] = 1
    # All mass in area 0
    v = np.zeros(12)
    v[0] = 1.0
    W = build_propagation_matrix(adj)
    out = diffuse_once(v, W, alpha=1.0)
    # With alpha=1, all mass goes through W; area 0's neighbors are 1 and 11
    assert out[1] > 0
    assert out[11] > 0
    assert out[0] >= 0
    # Areas not adjacent to 0 (e.g. 5, 6) get no mass from single step from 0
    # (they get 0 from v@W because W[0,:] is zero except 1 and 11)
    assert out[5] == 0
    assert out[6] == 0


def test_no_adjacency_no_diffusion():
    adj = np.zeros((12, 12), dtype=np.float64)
    W = build_propagation_matrix(adj)
    v = np.ones(12) / 12
    out = diffuse_once(v, W, alpha=0.5)
    # W is all zeros (no edges), so v @ W = 0, out = (1-alpha)*v = 0.5*v
    assert np.allclose(out, 0.5 * v)
