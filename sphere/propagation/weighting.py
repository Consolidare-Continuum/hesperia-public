# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Build propagation weights from topology; apply dynamism-based modulation.
Icosahedral topology: meta nodes (A6, A12) use reduced propagation weight on incident edges.
Uses core/math for row normalization. No duplicate math.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from core.math.matrix_utils import row_normalize


def normalize_weights(W: np.ndarray) -> np.ndarray:
    """
    Row-normalize weight matrix so each row sums to 1 (stochastic).
    Preserves diffusion stability: sum(W[i]) == 1 for all i with non-zero row.
    Zero rows are left as zeros.
    """
    return row_normalize(np.asarray(W, dtype=np.float64), fill_zero_rows=0.0)


def build_meta_filtered_edge_weights(
    adjacency: np.ndarray,
    meta_indices: frozenset[int] | set[int],
    *,
    scale: float = 0.5,
) -> np.ndarray:
    """
    Build 12×12 edge weight matrix for propagation with reduced weight on edges incident to meta nodes.
    Meta nodes (e.g. A6=5, A12=11) receive propagation normally but emit filtered propagation.
    On edges (i,j) where i in meta_indices or j in meta_indices, weight = scale; else 1.0.
    Only positions where adjacency[i,j]==1 are set; rest remain 0.
    """
    adj = np.asarray(adjacency, dtype=np.float64)
    if adj.shape != (12, 12):
        raise ValueError(f"adjacency must be 12x12, got {adj.shape}")
    meta = set(meta_indices)
    w = np.where(adj > 0, 1.0, 0.0)
    for i in range(12):
        for j in range(12):
            if adj[i, j] > 0 and (i in meta or j in meta):
                w[i, j] = scale
    return w


def build_edge_weight_matrix(
    adjacency: np.ndarray,
    edge_weights: np.ndarray | None = None,
) -> np.ndarray:
    """
    Build row-stochastic propagation matrix from adjacency.
    Mass flows only along edges (no adjacency -> no diffusion).
    If edge_weights is provided, same shape as adjacency; we use adjacency * edge_weights then row-normalize.
    """
    adj = np.asarray(adjacency, dtype=np.float64)
    if adj.shape != (12, 12):
        raise ValueError(f"adjacency must be 12x12, got {adj.shape}")
    if edge_weights is not None:
        w = np.asarray(edge_weights, dtype=np.float64)
        if w.shape != adj.shape:
            raise ValueError("edge_weights must match adjacency shape")
        # Only allow weights on edges; zero off-edges
        base = adj * w
    else:
        base = adj.copy()
    return row_normalize(base, fill_zero_rows=0.0)


def apply_stability_modulation(
    base_alpha: float,
    stability_index: float,
    *,
    k_stability: float = 0.5,
) -> float:
    """
    Higher stability -> lower effective diffusion (more persistent, less spread).
    effective = base_alpha * (1 - k_stability * stability_index), clamped to [0, 1].
    """
    if not (0 <= stability_index <= 1):
        stability_index = max(0.0, min(1.0, stability_index))
    factor = 1.0 - k_stability * stability_index
    return float(max(0.0, min(1.0, base_alpha * factor)))


def apply_jump_rate_modulation(
    base_alpha: float,
    jump_rate: float,
    *,
    k_jump: float = 0.3,
) -> float:
    """
    Higher jump rate -> slightly higher effective diffusion (more non-local moves).
    effective = base_alpha * (1 + k_jump * jump_rate), clamped to [0, 1].
    """
    if not (0 <= jump_rate <= 1):
        jump_rate = max(0.0, min(1.0, jump_rate))
    factor = 1.0 + k_jump * jump_rate
    return float(max(0.0, min(1.0, base_alpha * factor)))


def compute_effective_diffusion_rate(
    base_alpha: float,
    *,
    stability_index: float | None = None,
    jump_rate: float | None = None,
    k_stability: float = 0.5,
    k_jump: float = 0.3,
) -> float:
    """
    Apply stability and jump-rate modulation to base_alpha.
    Order: stability first, then jump rate. Deterministic.
    """
    alpha = base_alpha
    if stability_index is not None:
        alpha = apply_stability_modulation(alpha, stability_index, k_stability=k_stability)
    if jump_rate is not None:
        alpha = apply_jump_rate_modulation(alpha, jump_rate, k_jump=k_jump)
    return float(max(0.0, min(1.0, alpha)))
