# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Coverage: fraction of active families or areas.
Deterministic. Dimensions configurable via parameters.
"""

from __future__ import annotations

import numpy as np

from core.topology.invariant_catalog import AREAS as DEFAULT_NUM_AREAS, TOTAL_FAMILIES as DEFAULT_NUM_FAMILIES


def compute_family_coverage(
    family_counts: np.ndarray | list[int | float],
    *,
    num_families: int = DEFAULT_NUM_FAMILIES,
) -> float:
    """
    Family coverage = number_of_active_families / total_families.

    active_family: family_counts[f] > 0
    Returns coverage in [0, 1].
    """
    arr = np.asarray(family_counts, dtype=np.float64)
    if len(arr) != num_families:
        raise ValueError(f"family_counts must have length {num_families}, got {len(arr)}")
    if np.any(arr < 0):
        raise ValueError("family_counts must be non-negative")
    active = int(np.sum(arr > 0))
    return float(active / num_families)


def compute_area_coverage(
    area_vector: np.ndarray | list[int | float],
    *,
    num_areas: int = DEFAULT_NUM_AREAS,
) -> float:
    """
    Area coverage = number_of_active_areas / total_areas.
    active_area: area_vector[a] > 0. Returns coverage in [0, 1].
    """
    arr = np.asarray(area_vector, dtype=np.float64)
    if len(arr) != num_areas:
        raise ValueError(f"area_vector must have length {num_areas}, got {len(arr)}")
    if np.any(arr < 0):
        raise ValueError("area_vector must be non-negative")
    active = int(np.sum(arr > 0))
    return float(active / num_areas)
