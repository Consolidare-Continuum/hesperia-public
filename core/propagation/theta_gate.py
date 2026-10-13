# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3.1 — Θ gate (final output gate).
20_SPEC Release v0.3.1 Runtime Guards and Failure Classes.
governance = governance * (1 - gammaPenalty). If degraded: governance <= G_DEGRADED_MAX.
No extra API keys.
"""

from __future__ import annotations

from typing import Any

G_DEGRADED_MAX = 0.30
LOOP_DEGRADED_MAX = 0.2


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def apply_theta(
    result: dict[str, Any],
    gamma_penalty: float,
    degraded: bool,
) -> dict[str, Any]:
    """
    governance = governance * (1 - gammaPenalty).
    If degraded: governance <= G_DEGRADED_MAX.
    Returns new dict (same keys). No extra API keys.
    """
    out = dict(result)
    gamma_penalty = _clamp(gamma_penalty, 0.0, 1.0)
    gov = float(out.get("governance", 0.0))
    gov = gov * (1.0 - gamma_penalty)
    if degraded:
        gov = min(gov, G_DEGRADED_MAX)
    out["governance"] = _clamp(gov, 0.0, 1.0)
    return out
