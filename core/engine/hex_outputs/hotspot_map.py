# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Narrative hotspot map: local semantic pressure maxima."""

from __future__ import annotations

import numpy as np

__all__ = ["compute_hotspot_map"]


def compute_hotspot_map(
    hex_activation: np.ndarray,
    adjacency: list[list[int]],
    *,
    lam: float = 0.5,
) -> np.ndarray:
    """
    Hotspot(h) = A_h + λ Σ_{n∈N(h)} A_n
    """
    a = np.asarray(hex_activation, dtype=np.float64).reshape(-1)
    n = a.shape[0]
    if len(adjacency) != n:
        raise ValueError("adjacency length must match hex_activation")
    out = np.zeros(n, dtype=np.float64)
    for h in range(n):
        nb = adjacency[h]
        out[h] = float(a[h] + lam * sum(a[j] for j in nb))
    return out
