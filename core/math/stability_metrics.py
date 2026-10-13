# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Stability and tension metrics.
Deterministic formulas only. No pipeline or topology assumptions.
"""

from __future__ import annotations

import numpy as np

# Default dimensions (callers may override)
from core.topology.invariant_catalog import AREAS as DEFAULT_NUM_AREAS


def compute_stability_index(area_sequence: list[int] | np.ndarray) -> float:
    """
    Deterministic formula:

      repeated_stays = count of transitions where a_t == a_{t+1}
      total_transitions = len(area_sequence) - 1  (number of consecutive pairs)
      stability_index = repeated_stays / max(total_transitions, 1)

    High value = stable / persistent structure (many stays in same area).
    Low value = volatile movement (many changes).
    Sequence length 1: total_transitions = 0 → stability_index = 0.
    """
    arr = np.asarray(area_sequence, dtype=np.int64)
    n = len(arr)
    total_transitions = max(n - 1, 0)
    if total_transitions == 0:
        return 0.0

    repeated_stays = int(np.sum(arr[:-1] == arr[1:]))
    return float(repeated_stays / total_transitions)


def compute_structural_tension(
    area_vector: np.ndarray | list[float],
    *,
    num_areas: int = DEFAULT_NUM_AREAS,
) -> float:
    """
    Tension = 1 - (dominant_area_mass / total_mass).

    Where:
      dominant_area_mass = max(area_vector)
      total_mass = sum(area_vector)

    Interpretation: low tension → one area dominates; high tension → balanced competition.
    Return range: 0 ≤ tension ≤ 1. If total_mass == 0, returns 0.0.
    """
    arr = np.asarray(area_vector, dtype=np.float64)
    if len(arr) != num_areas:
        raise ValueError(f"area_vector must have length {num_areas}, got {len(arr)}")
    if np.any(arr < 0):
        raise ValueError("area_vector must be non-negative")
    total = float(np.sum(arr))
    if total <= 0:
        return 0.0
    dominant_mass = float(np.max(arr))
    return float(1.0 - (dominant_mass / total))
