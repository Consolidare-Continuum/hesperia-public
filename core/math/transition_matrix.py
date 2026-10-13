# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Transition count and probability matrices from area sequences.
Deterministic. No pipeline or topology assumptions.
"""

from __future__ import annotations

import numpy as np


def compute_transition_matrix(
    area_sequence: list[int] | np.ndarray,
    num_areas: int = 12,
) -> np.ndarray:
    """
    Build the area-to-area transition count matrix from consecutive pairs.

    Rule: for each pair (a_t, a_{t+1}), increment transition_matrix[a_t, a_{t+1}].
    Shape is always (num_areas, num_areas). Integer counts only.
    Deterministic ordering. No normalization.
    """
    arr = np.asarray(area_sequence, dtype=np.int64)
    matrix = np.zeros((num_areas, num_areas), dtype=np.int64)
    if arr.size < 2:
        return matrix
    for i in range(len(arr) - 1):
        a, b = int(arr[i]), int(arr[i + 1])
        if 0 <= a < num_areas and 0 <= b < num_areas:
            matrix[a, b] += 1
    return matrix


def compute_transition_probabilities(
    area_sequence: list[int] | np.ndarray,
    num_areas: int = 12,
) -> np.ndarray:
    """
    Row-normalize the transition count matrix so each row sums to 1.
    Rows with no outgoing transitions remain zero (no division).
    Raw count matrix remains canonical; this is an optional secondary output.
    """
    counts = compute_transition_matrix(area_sequence, num_areas=num_areas)
    row_sums = counts.sum(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        probs = np.where(row_sums > 0, counts / row_sums, 0.0)
    return np.asarray(probs, dtype=np.float64)
