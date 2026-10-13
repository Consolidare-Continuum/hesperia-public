# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Higher edge weights must produce larger propagated transfer than lower weights.
"""

from __future__ import annotations

import numpy as np
import pytest

from sphere.propagation.engine import compute_propagation
from sphere.propagation.diffusion import diffuse_once, build_propagation_matrix


def _ring_adjacency():
    adj = np.zeros((12, 12), dtype=np.float64)
    for i in range(12):
        adj[i, (i - 1) % 12] = 1
        adj[i, (i + 1) % 12] = 1
    return adj


def _family_to_area():
    return np.array([f // 24 for f in range(288)], dtype=np.int64)


def test_stronger_edge_gets_more_mass():
    adj = _ring_adjacency()
    # Area 0 -> neighbor 1 gets weight 2, neighbor 11 gets weight 1
    weights_strong_1 = adj.copy()
    weights_strong_1[0, 1] = 2.0
    weights_strong_1[0, 11] = 1.0
    W_strong_1 = build_propagation_matrix(adj, weights_strong_1)
    v = np.zeros(12)
    v[0] = 1.0
    out_strong = diffuse_once(v, W_strong_1, alpha=1.0)
    # More mass should go to 1 than to 11
    assert out_strong[1] > out_strong[11]
    assert out_strong[1] > 0
    assert out_strong[11] > 0


def test_uniform_weights_symmetric_flow():
    adj = _ring_adjacency()
    fa = _family_to_area()
    v = np.zeros(12)
    v[0] = 1.0
    # use_meta_filter=False so meta nodes (5, 11) don't get reduced weight; test expects uniform flow
    out = compute_propagation(
        v, np.zeros(288), adj, fa,
        base_alpha=1.0, normalize_output=False, use_meta_filter=False,
    )
    p = out["propagated_area_vector"]
    # Neighbors of 0 are 1 and 11; with uniform weights they get equal mass
    assert abs(p[1] - p[11]) < 1e-9
    assert p[1] > 0
