# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-7 canonical entrypoint: topology-driven propagation.
Orchestrates weighting, diffusion, family projection, diagnostics.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from core.math.vector_ops import vector_sum
from sphere.propagation.diffusion import (
    apply_damping,
    build_propagation_matrix,
    propagate_area_vector as _propagate_area_vector,
)
from sphere.propagation.family_projection import propagate_family_counts
from sphere.propagation.weighting import (
    compute_effective_diffusion_rate,
    build_meta_filtered_edge_weights,
)
from sphere.propagation.diagnostics import build_propagation_diagnostics
from sphere.topology import META_AREA_INDICES
from core.topology.invariant_catalog import AREAS as NUM_AREAS, TOTAL_FAMILIES as NUM_FAMILIES


def compute_propagation(
    area_vector: np.ndarray | list[float],
    family_counts: np.ndarray | list[float],
    adjacency: np.ndarray,
    family_to_area: np.ndarray,
    *,
    base_alpha: float = 0.5,
    edge_weights: np.ndarray | None = None,
    use_meta_filter: bool = True,
    normalize_output: bool = True,
    stability_index: float | None = None,
    jump_rate: float | None = None,
    transition_matrix: Any = None,
    curvature: float | None = None,
    num_steps: int = 1,
    damping_factor: float = 1.0,
) -> dict[str, Any]:
    """
    Real Layer-7 propagation: area diffusion over topology, then area→family projection.

    Inputs:
      area_vector: length 12
      family_counts: length 288 (used for consistency; output is derived from propagated area)
      adjacency: 12×12 from sphere/topology
      family_to_area: length 288 from sphere/topology
      base_alpha: diffusion strength [0,1]
      edge_weights: optional 12×12; if None and use_meta_filter True, meta nodes (A6, A12) get reduced weight
      normalize_output: if True, L1-normalize propagated area (and family) output
      stability_index, jump_rate: optional dynamism signals for alpha modulation

    Outputs:
      propagated_area_vector, propagated_family_counts, propagation_diagnostics,
      and optional propagation_matrix, effective_diffusion_rate, mass_before, mass_after.
    """
    adj = np.asarray(adjacency, dtype=np.float64)
    if adj.shape != (NUM_AREAS, NUM_AREAS):
        raise ValueError(f"adjacency must be {NUM_AREAS}x{NUM_AREAS}, got {adj.shape}")
    fa = np.asarray(family_to_area, dtype=np.int64)
    if fa.size != NUM_FAMILIES:
        raise ValueError(f"family_to_area must have length {NUM_FAMILIES}, got {fa.size}")

    _jump_rate: float | None = None
    if isinstance(jump_rate, (int, float)):
        _jump_rate = float(jump_rate)
    elif isinstance(jump_rate, dict) and "jump_rate" in jump_rate:
        _jump_rate = float(jump_rate["jump_rate"])
    alpha = compute_effective_diffusion_rate(
        base_alpha,
        stability_index=stability_index,
        jump_rate=_jump_rate,
    )
    stability_mod = stability_index is not None
    jump_mod = jump_rate is not None

    if edge_weights is None and use_meta_filter:
        edge_weights = build_meta_filtered_edge_weights(adj, META_AREA_INDICES, scale=0.5)
    W = build_propagation_matrix(adj, edge_weights)
    active_edges = int(vector_sum((adj > 0).astype(np.float64)))

    steps = max(1, int(num_steps))
    current_area = np.asarray(area_vector, dtype=np.float64)
    if current_area.size != NUM_AREAS:
        current_area = np.reshape(current_area, (NUM_AREAS,))
    aux = {"mass_before": 0.0, "mass_after": 0.0, "conservation_ok": True, "normalized": normalize_output, "alpha": alpha}
    # Per step: diffuse → normalize → apply_damping; if damping_factor < 1.0, normalize again.
    # Family projection only after final step (conservation).
    for _ in range(steps):
        propagated_area, aux = _propagate_area_vector(
            current_area,
            adj,
            alpha=alpha,
            edge_weights=edge_weights,
            normalize_output=normalize_output,
            num_areas=NUM_AREAS,
        )
        current_area = np.asarray(propagated_area, dtype=np.float64)
        current_area = apply_damping(current_area, damping_factor=damping_factor)
        if normalize_output and damping_factor < 1.0 and current_area.sum() > 0:
            from core.math.normalization import normalize_l1
            current_area = normalize_l1(current_area)
    propagated_family = propagate_family_counts(
        family_counts,
        current_area,
        fa,
        num_families=NUM_FAMILIES,
        num_areas=NUM_AREAS,
    )

    diag = build_propagation_diagnostics(
        diffusion_coefficient_used=alpha,
        stability_modulation_applied=stability_mod,
        jump_rate_modulation_applied=jump_mod,
        mass_before=aux["mass_before"],
        mass_after=aux["mass_after"],
        normalization_applied=normalize_output,
        conservation_ok=aux["conservation_ok"],
        active_edges_count=active_edges,
        num_areas=NUM_AREAS,
        num_families=NUM_FAMILIES,
        propagated_area_vector=current_area,
        propagated_family_counts=propagated_family,
    )

    return {
        "propagated_area_vector": current_area.tolist() if isinstance(current_area, np.ndarray) else list(current_area),
        "propagated_family_counts": propagated_family.tolist() if isinstance(propagated_family, np.ndarray) else list(propagated_family),
        "propagation_diagnostics": diag,
        "propagation_matrix": W.tolist(),
        "effective_diffusion_rate": alpha,
        "mass_before": aux["mass_before"],
        "mass_after": aux["mass_after"],
    }
