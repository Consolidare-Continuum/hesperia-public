# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-8 Shadow Correction Engine: filter weak propagation noise, stabilize signals.
Orchestrates suppression, dominance reinforcement, entropy correction; uses core.math only.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from core.math.entropy_metrics import compute_entropy
from core.math.stability_metrics import compute_structural_tension
from core.math.vector_ops import vector_sum

from sphere.propagation.family_projection import project_area_to_families
from sphere.shadow.suppression import apply_tail_suppression
from sphere.shadow.dominance_filter import apply_dominant_area_reinforcement
from sphere.shadow.entropy_correction import stabilize_entropy
from sphere.shadow.diagnostics import build_shadow_diagnostics
from core.topology.invariant_catalog import AREAS as NUM_AREAS, TOTAL_FAMILIES as NUM_FAMILIES


def compute_shadow_correction(
    propagated_area_vector: np.ndarray | list[float],
    propagated_family_counts: np.ndarray | list[float],
    propagation_diagnostics: dict[str, Any] | None = None,
    family_to_area: np.ndarray | None = None,
    *,
    structural_threshold: float = 0.01,
    dominance_boost_factor: float = 0.2,
    entropy_blend_strength: float = 0.2,
    num_areas: int = NUM_AREAS,
    num_families: int = NUM_FAMILIES,
) -> dict[str, Any]:
    """
    Run shadow correction: tail suppression → dominant reinforcement → entropy stabilization,
    then project corrected area vector to families. Recompute tension after correction.

    Inputs:
      propagated_area_vector: length 12
      propagated_family_counts: length 288 (used for consistency; output is area-derived)
      propagation_diagnostics: optional, from Layer-7
      family_to_area: length 288 for area→family projection; if None, use canonical f//24

    Outputs:
      corrected_area_vector, corrected_family_counts, shadow_diagnostics.
    """
    propagation_diagnostics = propagation_diagnostics or {}
    pv = np.asarray(propagated_area_vector, dtype=np.float64)
    if pv.size != num_areas:
        raise ValueError(f"propagated_area_vector must have length {num_areas}, got {pv.size}")
    if np.any(pv < 0):
        raise ValueError("propagated_area_vector must be non-negative")

    if family_to_area is None:
        family_to_area = np.array([f // 24 for f in range(num_families)], dtype=np.int64)
    fa = np.asarray(family_to_area, dtype=np.int64)
    if fa.size != num_families:
        raise ValueError(f"family_to_area must have length {num_families}, got {fa.size}")

    # Tension before
    tension_before = compute_structural_tension(pv, num_areas=num_areas)
    entropy_before_init = compute_entropy(pv)

    # 1. Tail suppression
    suppressed, count_suppressed, mass_retained = apply_tail_suppression(
        pv, structural_threshold=structural_threshold
    )
    total_after_supp = vector_sum(suppressed)
    if total_after_supp <= 0:
        # All suppressed -> return zeros with diagnostics
        corrected_area = np.zeros(num_areas, dtype=np.float64)
        corrected_family = np.zeros(num_families, dtype=np.float64)
        diag = build_shadow_diagnostics(
            tail_suppression_count=count_suppressed,
            structural_threshold=structural_threshold,
            mass_retained_after_suppression=0.0,
            dominance_boost_factor=dominance_boost_factor,
            entropy_before=entropy_before_init,
            entropy_after=0.0,
            tension_before=tension_before,
            tension_after=0.0,
            normalized=True,
        )
        return {
            "corrected_area_vector": corrected_area.tolist(),
            "corrected_family_counts": corrected_family.tolist(),
            "shadow_diagnostics": diag,
        }
    suppressed = suppressed / total_after_supp

    # 2. Dominant area reinforcement
    reinforced = apply_dominant_area_reinforcement(
        suppressed, boost_factor=dominance_boost_factor, num_areas=num_areas
    )

    # 3. Entropy stabilization
    corrected_area, entropy_before_blend, entropy_after = stabilize_entropy(
        reinforced,
        blend_strength=entropy_blend_strength,
        num_areas=num_areas,
    )

    # 4. Project to families
    corrected_family = project_area_to_families(
        corrected_area, fa, num_families=num_families, num_areas=num_areas
    )

    # 5. Tension after
    tension_after = compute_structural_tension(corrected_area, num_areas=num_areas)

    diag = build_shadow_diagnostics(
        tail_suppression_count=count_suppressed,
        structural_threshold=structural_threshold,
        mass_retained_after_suppression=mass_retained,
        dominance_boost_factor=dominance_boost_factor,
        entropy_before=entropy_before_init,
        entropy_after=entropy_after,
        tension_before=tension_before,
        tension_after=tension_after,
        normalized=True,
    )

    return {
        "corrected_area_vector": corrected_area.tolist() if isinstance(corrected_area, np.ndarray) else list(corrected_area),
        "corrected_family_counts": corrected_family.tolist() if isinstance(corrected_family, np.ndarray) else list(corrected_family),
        "shadow_diagnostics": diag,
    }
