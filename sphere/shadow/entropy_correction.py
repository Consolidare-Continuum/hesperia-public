# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Entropy stabilization: reduce entropy increase caused by diffusion.
Uses core.math entropy and normalization only.
"""

from __future__ import annotations

import numpy as np

from core.math.entropy_metrics import compute_entropy
from core.math.vector_ops import detect_dominant_area, vector_sum
from core.math.normalization import normalize_l1


def stabilize_entropy(
    area_vector: np.ndarray | list[float],
    *,
    max_entropy_increase: float = 0.1,
    blend_strength: float = 0.3,
    num_areas: int = 12,
) -> tuple[np.ndarray, float, float]:
    """
    If entropy increased above baseline, blend toward a more peaked (dominant-only) distribution
    to cap entropy. Returns (corrected_vector, entropy_before, entropy_after).
    """
    arr = np.asarray(area_vector, dtype=np.float64)
    if arr.size != num_areas:
        raise ValueError(f"area_vector must have length {num_areas}, got {arr.size}")
    if np.any(arr < 0):
        raise ValueError("area_vector must be non-negative")
    total = vector_sum(arr)
    if total <= 0:
        return arr, 0.0, 0.0
    entropy_before = compute_entropy(arr)
    dom_idx = detect_dominant_area(arr, num_areas=num_areas)
    # Peaked: all mass on dominant
    peaked = np.zeros(num_areas, dtype=np.float64)
    peaked[dom_idx] = 1.0
    # Optional: blend with peaked to reduce entropy if desired
    blended = (1.0 - blend_strength) * arr + blend_strength * peaked * total
    blended = np.maximum(blended, 0.0)
    corrected = normalize_l1(blended)
    entropy_after = compute_entropy(corrected)
    return corrected, entropy_before, entropy_after
