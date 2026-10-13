# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-6 Dynamism Engine.
Orchestrates deterministic movement metrics from ordered family/area sequences.
Produces trajectory, transition matrix, curvature, jump rate, and stability index.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from core.math import (
    build_trajectory,
    compress_trajectory,
    compute_curvature,
    compute_jump_rate,
    compute_stability_index,
    compute_transition_matrix,
)


def _validate_inputs(
    area_sequence: list[int] | np.ndarray,
    adjacency_matrix: np.ndarray,
) -> None:
    if len(area_sequence) < 1:
        raise ValueError("area_sequence must have length >= 1 (empty sequence not allowed)")
    if adjacency_matrix.shape != (12, 12):
        raise ValueError(
            f"adjacency_matrix must have shape (12, 12), got {adjacency_matrix.shape}"
        )
    arr = np.asarray(area_sequence, dtype=np.int64)
    if not np.all((arr >= 0) & (arr < 12)):
        raise ValueError("all area_sequence values must be in [0, 11]")


def compute_dynamism(
    family_sequence: list[int] | np.ndarray,
    area_sequence: list[int] | np.ndarray,
    adjacency_matrix: np.ndarray,
) -> dict[str, Any]:
    """
    Layer-6 entrypoint: compute deterministic dynamism artifact from ordered sequences.

    Inputs:
      family_sequence: ordered family ids (used for consistency; area_sequence drives metrics).
      area_sequence: ordered area ids 0..11 reflecting text flow.
      adjacency_matrix: 12×12 binary area adjacency (e.g. from topology loader).

    Returns canonical artifact:
      trajectory: { raw, compressed }
      transition_matrix: 12×12 count matrix (list of lists for JSON-serializability)
      curvature: float
      jump_rate: { jump_count, jump_rate }
      stability_index: float

    Edge cases:
      - Sequence length 1: transition_matrix zeros, jump_rate 0, curvature 0, stability_index 0.
      - Empty sequence: ValueError.
    """
    _validate_inputs(area_sequence, adjacency_matrix)

    raw = build_trajectory(area_sequence)
    compressed = compress_trajectory(area_sequence, segment_form=False)
    segments = compress_trajectory(area_sequence, segment_form=True)

    trans = compute_transition_matrix(area_sequence, num_areas=12)
    curv = compute_curvature(area_sequence, adjacency_matrix)
    jump = compute_jump_rate(area_sequence, adjacency_matrix)
    stab = compute_stability_index(area_sequence)

    return {
        "trajectory": {
            "raw": raw,
            "compressed": compressed,
            "segments": segments,
        },
        "transition_matrix": trans.tolist(),
        "curvature": curv,
        "jump_rate": jump,
        "stability_index": stab,
    }
