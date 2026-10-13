# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3 — Σ invariant enforcer.
19_SPEC Release v0.3 Structural Enforcement.
Static geometry, indexing bijection, output contract, domain clamp.
Fail → HARD_STOP (raise). No bypass. No silent ontology correction.
"""

from __future__ import annotations

from typing import Any

from .failure_classes import FailureClass
from core.topology.invariant_catalog import (
    AREAS,
    AREA_FAMILY_MAP,
    CANONICAL_AREA_SET,
    FAMILIES_PER_AREA,
    HEXES_PER_FAMILY,
    SIDES_PER_HEX,
    TOTAL_SIDES,
    forward,
    inverse,
)

# Required API output keys (exactly 6) and numeric types
REQUIRED_OUTPUT_KEYS = frozenset({
    "governance", "loopability", "tension_energy", "obstacle_score",
    "dominant_family", "dominant_area",
})


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# -----------------------------------------------------------------------------
# 2.1 Static geometry checks
# -----------------------------------------------------------------------------

def check_geometry(
    num_areas: int,
    families_per_area: int,
    hex_upper: int,
    side_upper: int,
) -> None:
    """
    areas == 12, families per area == 24, hex bounds valid, side bounds valid.
    Raises on failure (HARD_STOP).
    """
    if num_areas != AREAS:
        raise RuntimeError(
            f"Sigma HARD_STOP: areas must be {AREAS}, got {num_areas}"
        ) from None
    if families_per_area != FAMILIES_PER_AREA:
        raise RuntimeError(
            f"Sigma HARD_STOP: families_per_area must be {FAMILIES_PER_AREA}, got {families_per_area}"
        ) from None
    if hex_upper != HEXES_PER_FAMILY:
        raise RuntimeError(
            f"Sigma HARD_STOP: hex bound must be {HEXES_PER_FAMILY}, got {hex_upper}"
        ) from None
    if side_upper != SIDES_PER_HEX:
        raise RuntimeError(
            f"Sigma HARD_STOP: side bound must be {SIDES_PER_HEX}, got {side_upper}"
        ) from None


# -----------------------------------------------------------------------------
# 2.2 Indexing bijection check
# -----------------------------------------------------------------------------

def check_bijection() -> None:
    """
    forward(area, familyLocal, hexLocal, sideLocal) then inverse(sideId) must be identity.
    Raises on failure (HARD_STOP).
    """
    for area in range(AREAS):
        for fl in range(FAMILIES_PER_AREA):
            for h in range(HEXES_PER_FAMILY):
                for s in range(SIDES_PER_HEX):
                    sid = forward(area, fl, h, s)
                    a2, fl2, h2, s2 = inverse(sid)
                    if (area, fl, h, s) != (a2, fl2, h2, s2):
                        raise RuntimeError(
                            f"Sigma HARD_STOP: bijection failed at ({area},{fl},{h},{s}) -> {sid} -> ({a2},{fl2},{h2},{s2})"
                        ) from None
    # inverse for every sideId in range
    for sid in range(TOTAL_SIDES):
        a, fl, h, s = inverse(sid)
        sid2 = forward(a, fl, h, s)
        if sid != sid2:
            raise RuntimeError(
                f"Sigma HARD_STOP: inverse identity failed sideId={sid} -> ({a},{fl},{h},{s}) -> {sid2}"
            ) from None


# -----------------------------------------------------------------------------
# 2.3 Output contract validator
# -----------------------------------------------------------------------------

def validate_output_contract(result: dict[str, Any]) -> None:
    """
    Exactly 6 keys, exactly correct names, correct numeric types.
    Raises on failure (HARD_STOP).
    """
    keys = set(result.keys())
    if keys != REQUIRED_OUTPUT_KEYS:
        extra = keys - REQUIRED_OUTPUT_KEYS
        missing = REQUIRED_OUTPUT_KEYS - keys
        if extra or missing:
            raise RuntimeError(
                f"Sigma HARD_STOP: output must have exactly keys {REQUIRED_OUTPUT_KEYS}; missing={missing!r} extra={extra!r}"
            ) from None
    for k in REQUIRED_OUTPUT_KEYS:
        v = result[k]
        if k in ("governance", "loopability", "tension_energy", "obstacle_score"):
            if not isinstance(v, (int, float)):
                raise RuntimeError(
                    f"Sigma HARD_STOP: {k} must be numeric, got {type(v).__name__}"
                ) from None
        else:  # dominant_family, dominant_area
            if v is not None and not isinstance(v, int):
                raise RuntimeError(
                    f"Sigma HARD_STOP: {k} must be int or None, got {type(v).__name__}"
                ) from None


# -----------------------------------------------------------------------------
# 2.4 Domain clamp layer
# -----------------------------------------------------------------------------

def clamp_domain(data: dict[str, Any]) -> dict[str, Any]:
    """
    governance, loopability ∈ [0,1]; tension_energy, obstacle_score ≥ 0.
    Clamping only; no silent ontology correction.
    Returns new dict with clamped values (same keys).
    """
    out = dict(data)
    if "governance" in out:
        out["governance"] = _clamp(float(out["governance"]), 0.0, 1.0)
    if "loopability" in out:
        out["loopability"] = _clamp(float(out["loopability"]), 0.0, 1.0)
    if "tension_energy" in out:
        v = float(out["tension_energy"])
        out["tension_energy"] = v if v >= 0 else 0.0
    if "obstacle_score" in out:
        v = float(out["obstacle_score"])
        out["obstacle_score"] = v if v >= 0 else 0.0
    return out


# -----------------------------------------------------------------------------
# Ontology check: area name in canonical set (for DATA_REJECT / typo reject)
# -----------------------------------------------------------------------------

def check_area_canonical(area_name: str) -> bool:
    """True if area_name in CANONICAL_AREA_SET."""
    return area_name in CANONICAL_AREA_SET


def check_family_in_area(area_name: str, family_name: str) -> bool:
    """True if area in map and family in that area's 24."""
    if area_name not in AREA_FAMILY_MAP:
        return False
    return family_name in AREA_FAMILY_MAP[area_name]


# -----------------------------------------------------------------------------
# Sigma.enforce(summary): full execution_flow for engine output
# -----------------------------------------------------------------------------

def enforce(
    result: dict[str, Any],
    *,
    skip_geometry: bool = False,
    skip_bijection: bool = False,
) -> dict[str, Any]:
    """
    Run geometry (optional), bijection (optional), output contract, domain clamp.
    Result must have exactly the 6 required keys (no extra). Raises on contract failure.
    """
    if not skip_geometry:
        check_geometry(AREAS, FAMILIES_PER_AREA, HEXES_PER_FAMILY, SIDES_PER_HEX)
    if not skip_bijection:
        check_bijection()
    validate_output_contract(result)
    return clamp_domain(dict(result))
