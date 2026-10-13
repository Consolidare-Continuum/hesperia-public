# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Contradiction front map: tension on semantic boundaries."""

from __future__ import annotations

import numpy as np

__all__ = ["compute_contradiction_front"]


def compute_contradiction_front(
    hex_activation: np.ndarray,
    adjacency: list[list[int]],
    contradiction_matrix: np.ndarray,
) -> np.ndarray:
    """
    Front(h) = Σ_{j∈N(h)} |A_h − A_j| · C_{hj}
    """
    a = np.asarray(hex_activation, dtype=np.float64).reshape(-1)
    c = np.asarray(contradiction_matrix, dtype=np.float64)
    n = a.shape[0]
    if c.shape != (n, n):
        raise ValueError("contradiction_matrix must be (N,N)")
    if len(adjacency) != n:
        raise ValueError("adjacency length must match hex_activation")
    out = np.zeros(n, dtype=np.float64)
    for h in range(n):
        s = 0.0
        for j in adjacency[h]:
            s += abs(float(a[h] - a[j])) * float(c[h, j])
        out[h] = s
    return out
