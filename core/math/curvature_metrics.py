# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Curvature and jump rate metrics from area sequences and adjacency.
Deterministic, bounded. No pipeline logic.
"""

from __future__ import annotations

import numpy as np

# Scoring (deterministic)
SAME_AREA = 0.0
ADJACENT_MOVE = 1.0
NON_ADJACENT_MOVE = 2.0


def compute_curvature(
    area_sequence: list[int] | np.ndarray,
    adjacency_matrix: np.ndarray,
) -> float:
    """
    Structural curvature: average step score over all transitions.

    Per-step scores:
      - Same area (a_t == a_{t+1}): 0.0  (no curvature event)
      - Move to adjacent area:       1.0  (low curvature)
      - Move to non-adjacent area:   2.0  (high curvature)

    Formula:
      curvature = sum(step_curvature_scores) / max(number_of_transitions, 1)

    number_of_transitions = len(area_sequence) - 1.
    Sequence length 1: curvature = 0.
    Bounded: result in [0, 2]. Reproducible and deterministic.
    """
    arr = np.asarray(area_sequence, dtype=np.int64)
    n = len(arr)
    num_transitions = max(n - 1, 0)
    if num_transitions == 0:
        return 0.0

    total = 0.0
    for i in range(n - 1):
        a, b = int(arr[i]), int(arr[i + 1])
        if a == b:
            total += SAME_AREA
        elif adjacency_matrix[a, b] != 0:
            total += ADJACENT_MOVE
        else:
            total += NON_ADJACENT_MOVE

    return float(total / num_transitions)


def compute_jump_rate(
    area_sequence: list[int] | np.ndarray,
    adjacency_matrix: np.ndarray,
) -> dict[str, int | float]:
    """
    A jump is any transition where source != target and source and target are not adjacent.

    Formula:
      jump_rate = jump_count / max(total_transitions, 1)

    total_transitions = number of consecutive pairs (len(sequence) - 1).
    Returns {"jump_count": int, "jump_rate": float}.
    """
    arr = np.asarray(area_sequence, dtype=np.int64)
    n = len(arr)
    total_transitions = max(n - 1, 0)
    if total_transitions == 0:
        return {"jump_count": 0, "jump_rate": 0.0}

    jump_count = 0
    for i in range(n - 1):
        a, b = int(arr[i]), int(arr[i + 1])
        if a != b and adjacency_matrix[a, b] == 0:
            jump_count += 1

    rate = jump_count / total_transitions
    return {"jump_count": jump_count, "jump_rate": float(rate)}
