# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Dominant area reinforcement: boost dominant areas/families relative to background noise.
Uses core.math for dominance and normalization only.
"""

from __future__ import annotations

import numpy as np

from core.math.vector_ops import detect_dominant_area, vector_sum
from core.math.normalization import normalize_l1


def apply_dominant_area_reinforcement(
    area_vector: np.ndarray | list[float],
    *,
    boost_factor: float = 0.2,
    num_areas: int = 12,
) -> np.ndarray:
    """
    Boost mass on the dominant area by (1 + boost_factor), then L1-renormalize.
    Deterministic. Preserves non-negativity and sum 1 after norm.
    """
    arr = np.asarray(area_vector, dtype=np.float64)
    if arr.size != num_areas:
        raise ValueError(f"area_vector must have length {num_areas}, got {arr.size}")
    if np.any(arr < 0):
        raise ValueError("area_vector must be non-negative")
    total = vector_sum(arr)
    if total <= 0:
        return arr
    dom_idx = detect_dominant_area(arr, num_areas=num_areas)
    out = arr.copy()
    out[dom_idx] = out[dom_idx] * (1.0 + boost_factor)
    return normalize_l1(out)
