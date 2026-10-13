# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Semantic nucleus / cluster gravity field."""

from __future__ import annotations

import numpy as np

__all__ = ["compute_cluster_gravity"]


def compute_cluster_gravity(
    hex_activation: np.ndarray,
    distance_matrix: np.ndarray,
    *,
    eps: float = 1e-6,
) -> np.ndarray:
    """
    G(h) = Σ_i A_i / (d(h,i) + ε)², excluding i=h (or use large d(h,h)).
    """
    a = np.asarray(hex_activation, dtype=np.float64).reshape(-1)
    d = np.asarray(distance_matrix, dtype=np.float64)
    n = a.shape[0]
    if d.shape != (n, n):
        raise ValueError("distance_matrix must be (N,N)")
    g = np.zeros(n, dtype=np.float64)
    for h in range(n):
        s = 0.0
        for i in range(n):
            if i == h:
                continue
            dist = max(float(d[h, i]), eps)
            s += float(a[i]) / (dist * dist)
        g[h] = s
    return g
