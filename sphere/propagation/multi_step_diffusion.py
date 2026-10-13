# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Multi-step propagation: v_k = v W^k and iterative (1-α)v + α(vW).
Provides propagation_depth_metric for vector sequences.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from core.math.normalization import normalize_l1


def propagate_k_steps(
    vector: np.ndarray | list[float],
    matrix: np.ndarray,
    k: int,
    *,
    normalize: bool = True,
) -> np.ndarray:
    """
    Pure power diffusion: v_k = v @ W^k.
    k=1: v @ W. k>1: spreads influence over k hops.
    """
    v = np.asarray(vector, dtype=np.float64).flatten()
    W = np.asarray(matrix, dtype=np.float64)
    if v.size != W.shape[0] or W.shape[0] != W.shape[1]:
        raise ValueError("vector length must match matrix shape (n x n)")
    if k < 1:
        k = 1
    Wk = np.linalg.matrix_power(W, k)
    out = v @ Wk
    out = np.maximum(out, 0.0)
    if normalize and out.sum() > 0:
        out = normalize_l1(out)
    return out


def iterative_diffusion(
    vector: np.ndarray | list[float],
    matrix: np.ndarray,
    iterations: int,
    alpha: float,
    *,
    normalize: bool = True,
) -> np.ndarray:
    """
    Iterative step: current = (1-α)*current + α*(current @ W).
    Same as current engine step repeated; k=1 matches single-step output.
    """
    from core.math.diffusion import diffuse_step

    v = np.asarray(vector, dtype=np.float64).flatten()
    W = np.asarray(matrix, dtype=np.float64)
    if v.size != W.shape[0] or W.shape[0] != W.shape[1]:
        raise ValueError("vector length must match matrix shape (n x n)")
    if iterations < 1:
        iterations = 1
    current = v.copy()
    for _ in range(iterations):
        current = diffuse_step(current, W, alpha)
        current = np.maximum(current, 0.0)
        if normalize and current.sum() > 0:
            current = normalize_l1(current)
    return current


def propagation_depth_metric(vector_sequence: list[np.ndarray] | list[list[float]]) -> dict[str, Any]:
    """
    Metrics over a sequence of vectors (e.g. v, vW, vW^2, ...).
    Returns spread (e.g. L1 distances between consecutive), entropy progression, etc.
    """
    if not vector_sequence or len(vector_sequence) < 2:
        return {"depth": 0, "consecutive_l1": [], "entropy_sequence": []}

    seq = [np.asarray(x, dtype=np.float64).flatten() for x in vector_sequence]
    n = len(seq[0])
    if not all(len(x) == n for x in seq):
        return {"depth": 0, "consecutive_l1": [], "entropy_sequence": []}

    from core.math.vector_ops import vector_sum

    consecutive_l1 = []
    for i in range(len(seq) - 1):
        d = float(vector_sum(np.abs(seq[i + 1] - seq[i])))
        consecutive_l1.append(d)

    from core.math.entropy_metrics import compute_normalized_entropy

    entropy_sequence = [compute_normalized_entropy(s) for s in seq]

    return {
        "depth": len(vector_sequence) - 1,
        "consecutive_l1": consecutive_l1,
        "entropy_sequence": entropy_sequence,
    }


__all__ = [
    "propagate_k_steps",
    "iterative_diffusion",
    "propagation_depth_metric",
]
