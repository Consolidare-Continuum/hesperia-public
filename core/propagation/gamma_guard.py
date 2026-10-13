# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3.1 — Γ guard (traversal stability).
20_SPEC Release v0.3.1 Runtime Guards and Failure Classes.
Inputs: traversal_length, area_hop_count, loopability.
Output: gammaPenalty ∈ [0,1]. Hard rule: Gamma cannot increase governance.
"""

from __future__ import annotations


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_gamma_penalty(
    traversal_length: int,
    area_hop_count: int,
    loopability: float,
) -> float:
    """
    gammaPenalty ∈ [0,1]. Higher traversal/area hops and lower loopability → higher penalty.
    Gamma cannot increase governance (penalty only reduces or leaves unchanged).
    """
    loopability = _clamp(loopability, 0.0, 1.0)
    # Stability: long traversal and many area hops increase penalty; low loopability increases penalty
    length_factor = min(1.0, max(0.0, traversal_length / 20.0)) if traversal_length else 0.0
    hop_factor = min(1.0, max(0.0, area_hop_count / 10.0)) if area_hop_count else 0.0
    loop_factor = 1.0 - loopability
    raw = 0.4 * length_factor + 0.35 * hop_factor + 0.25 * loop_factor
    # Explicit bound: never trust math. gammaPenalty ∈ [0, 1] always.
    return _clamp(float(raw), 0.0, 1.0)
