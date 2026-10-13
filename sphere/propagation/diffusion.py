# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Area-level diffusion over the topology. Uses core/math only.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from core.math.diffusion import diffuse_step
from core.math.normalization import normalize_l1
from core.math.conservation import check_mass_conservation
from core.math.vector_ops import vector_sum


def diffuse_once(
    area_vector: np.ndarray | list[float],
    propagation_matrix: np.ndarray,
    alpha: float,
) -> np.ndarray:
    """
    One diffusion step: (1-alpha)*v + alpha*(v @ W). Uses core.math.diffusion.
    """
    return diffuse_step(area_vector, propagation_matrix, alpha)


def apply_damping(
    vector: np.ndarray | list[float],
    damping_factor: float = 1.0,
) -> np.ndarray:
    """
    Apply damping to vector (e.g. per-step decay). Default 1.0 = identity.
    Used in multi-step propagation after each diffuse+normalize step.
    """
    v = np.asarray(vector, dtype=np.float64)
    if damping_factor <= 0.0 or damping_factor > 1.0:
        return v
    return v * damping_factor


def build_propagation_matrix(
    adjacency: np.ndarray,
    edge_weights: np.ndarray | None = None,
) -> np.ndarray:
    """Row-stochastic W from adjacency (and optional weights). Delegates to weighting."""
    from sphere.propagation.weighting import build_edge_weight_matrix
    return build_edge_weight_matrix(adjacency, edge_weights)


def propagate_area_vector(
    area_vector: np.ndarray | list[float],
    adjacency: np.ndarray,
    *,
    alpha: float = 0.5,
    edge_weights: np.ndarray | None = None,
    normalize_output: bool = True,
    num_areas: int = 12,
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Real area diffusion: new = (1-alpha)*v + alpha*(v @ W), W from adjacency.
    Returns (propagated_vector, aux) with aux containing mass_before, mass_after, conservation_ok, etc.
    """
    v = np.asarray(area_vector, dtype=np.float64)
    if v.size != num_areas:
        raise ValueError(f"area_vector must have length {num_areas}, got {v.size}")
    if np.any(v < 0):
        raise ValueError("area_vector must be non-negative")
    W = build_propagation_matrix(adjacency, edge_weights)
    mass_before = vector_sum(v)
    out = diffuse_once(v, W, alpha)
    out = np.maximum(out, 0.0)
    mass_after = vector_sum(out)
    conservation_ok = check_mass_conservation(v, out, relative_tolerance=1e-5)
    if normalize_output and mass_after > 0:
        out = normalize_l1(out)
        mass_after = vector_sum(out)
    return out, {
        "mass_before": mass_before,
        "mass_after": mass_after,
        "conservation_ok": conservation_ok,
        "normalized": normalize_output,
        "alpha": alpha,
    }
