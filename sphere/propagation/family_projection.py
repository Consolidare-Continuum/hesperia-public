# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Map propagated area influence back to family space (288). Uses family→area mapping only.
"""

from __future__ import annotations

import numpy as np

from core.math.vector_ops import vector_sum


def build_family_area_projection(
    family_to_area: np.ndarray,
    num_families: int = 288,
    num_areas: int = 12,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Precompute per-area family counts and which families belong to which area.
    Returns (families_per_area: length 12, family_to_area as given).
    """
    fa = np.asarray(family_to_area, dtype=np.int64)
    if fa.size != num_families:
        raise ValueError(f"family_to_area must have length {num_families}, got {fa.size}")
    if np.any((fa < 0) | (fa >= num_areas)):
        raise ValueError("family_to_area entries must be in [0, num_areas-1]")
    families_per_area = np.zeros(num_areas, dtype=np.int64)
    for a in range(num_areas):
        families_per_area[a] = int(vector_sum((fa == a).astype(np.float64)))
    return families_per_area, fa


def project_area_to_families(
    propagated_area_vector: np.ndarray,
    family_to_area: np.ndarray,
    *,
    num_families: int = 288,
    num_areas: int = 12,
) -> np.ndarray:
    """
    Distribute each area's propagated mass uniformly over its families.
    propagated_family_counts[f] = propagated_area_vector[a] / count(families in a),
    where a = family_to_area[f]. Preserves total mass (sum over families = sum over areas).
    """
    pv = np.asarray(propagated_area_vector, dtype=np.float64)
    if pv.size != num_areas:
        raise ValueError(f"propagated_area_vector must have length {num_areas}, got {pv.size}")
    families_per_area, fa = build_family_area_projection(
        family_to_area, num_families=num_families, num_areas=num_areas
    )
    out = np.zeros(num_families, dtype=np.float64)
    for a in range(num_areas):
        n = families_per_area[a]
        if n > 0 and pv[a] >= 0:
            out[fa == a] = pv[a] / n
    return out


def propagate_family_counts(
    family_counts: np.ndarray | list[float],
    propagated_area_vector: np.ndarray,
    family_to_area: np.ndarray,
    *,
    num_families: int = 288,
    num_areas: int = 12,
) -> np.ndarray:
    """
    Family-level output from area propagation: project propagated area vector to families.
    This is Option A (area-driven): we do not copy family_counts; we derive from propagated_area_vector.
    """
    return project_area_to_families(
        propagated_area_vector,
        family_to_area,
        num_families=num_families,
        num_areas=num_areas,
    )
