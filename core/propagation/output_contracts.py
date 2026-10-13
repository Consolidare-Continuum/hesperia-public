# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3.2 — canonical output contracts (26_SPEC §2).
Minimal operational result (6 keys); minimal error result (3 keys).
All floats finite; no extra keys.
"""

from __future__ import annotations

import math
from typing import Any


def to_minimal_operational_result(result: dict[str, Any]) -> dict[str, Any]:
    """
    Convert internal 6-key result to v0.3.2 minimal operational result.
    dominant_area ∈ [0,11], dominant_family ∈ [0,287]; None → 0.
    All floats finite (no NaN/Inf).
    """
    da = result.get("dominant_area")
    df = result.get("dominant_family")
    da = int(da) if da is not None else 0
    df = int(df) if df is not None else 0
    da = max(0, min(11, da))
    df = max(0, min(287, df))
    g = float(result.get("governance", 0.0))
    l = float(result.get("loopability", 0.0))
    t = float(result.get("tension_energy", 0.0))
    o = float(result.get("obstacle_score", 0.0))
    if not math.isfinite(g):
        g = 0.0
    if not math.isfinite(l):
        l = 0.0
    if not math.isfinite(t):
        t = 0.0
    if not math.isfinite(o):
        o = 0.0
    out = {
        "dominant_area": da,
        "dominant_family": df,
        "governance": g,
        "loopability": l,
        "tension_energy": t,
        "obstacle_score": o,
    }
    # Non-breaking semantic aliases for clearer API language.
    out["constraint_status"] = g
    out["structural_recurrence"] = l
    out["resistance_index"] = o
    return out


def make_error_result(message: str, code: int = 500) -> dict[str, Any]:
    """v0.3.2 minimal error summary: exactly 3 keys (26_SPEC §2.2)."""
    return {
        "error": True,
        "message": str(message),
        "code": int(code),
    }
