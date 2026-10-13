# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Propagation diagnostics: diffusion coefficient, mass, normalization, edge counts.
"""

from __future__ import annotations

from typing import Any


def build_propagation_diagnostics(
    *,
    diffusion_coefficient_used: float,
    stability_modulation_applied: bool = False,
    jump_rate_modulation_applied: bool = False,
    mass_before: float = 0.0,
    mass_after: float = 0.0,
    normalization_applied: bool = False,
    conservation_ok: bool = False,
    active_edges_count: int = 0,
    num_areas: int = 12,
    num_families: int = 288,
    propagated_area_vector: Any = None,
    propagated_family_counts: Any = None,
) -> dict[str, Any]:
    """
    Build a deterministic diagnostics dict for Layer-7.
    """
    out: dict[str, Any] = {
        "diffusion_coefficient_used": diffusion_coefficient_used,
        "stability_modulation_applied": stability_modulation_applied,
        "jump_rate_modulation_applied": jump_rate_modulation_applied,
        "mass_before": mass_before,
        "mass_after": mass_after,
        "normalization_applied": normalization_applied,
        "conservation_ok": conservation_ok,
        "active_edges_count": active_edges_count,
        "num_areas": num_areas,
        "num_families": num_families,
    }
    if propagated_area_vector is not None:
        try:
            n = len(propagated_area_vector)
            out["propagated_area_vector_length"] = n
            out["changed_areas_count"] = n  # can be refined to count non-zero
        except Exception:
            pass
    if propagated_family_counts is not None:
        try:
            n = len(propagated_family_counts)
            out["propagated_family_counts_length"] = n
            out["changed_families_count"] = n
        except Exception:
            pass
    return out
