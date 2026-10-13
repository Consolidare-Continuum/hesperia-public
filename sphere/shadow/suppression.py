# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Tail suppression: remove propagation values below structural threshold.
Uses core.math for sums; no duplicate math.
"""

from __future__ import annotations

import numpy as np

from core.math.vector_ops import vector_sum


def apply_tail_suppression(
    vector: np.ndarray | list[float],
    *,
    structural_threshold: float = 0.01,
) -> tuple[np.ndarray, int, float]:
    """
    Zero out entries below structural_threshold. Preserve non-negative values above threshold.
    Returns (suppressed_vector, count_suppressed, mass_retained).
    """
    arr = np.asarray(vector, dtype=np.float64).flatten()
    if structural_threshold < 0:
        structural_threshold = 0.0
    out = np.where(arr >= structural_threshold, arr, 0.0).astype(np.float64)
    below = (arr < structural_threshold) & (arr > 0)
    count_suppressed = int(vector_sum(below.astype(np.float64)))
    mass_before = vector_sum(arr)
    mass_after = vector_sum(out)
    mass_retained = mass_after if mass_before > 0 else 0.0
    return out, count_suppressed, mass_retained
