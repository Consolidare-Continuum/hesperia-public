# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA L1 Normative Structure Profile (34_SPEC N1 / Profile Extension).
Schema and loader for externally defined StructureProfile. No inference; profiles are versioned artifacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, TypedDict


# L1 Profile Taxonomy (canonical): primary_axis and strictness_level prevent profile sprawl
PRIMARY_AXIS_VALUES = frozenset(("distribution", "concentration", "altitude", "constraint", "regression"))
STRICTNESS_LEVEL_VALUES = frozenset(("soft", "medium", "hard"))


class StructureProfile(TypedDict, total=False):
    """StructureProfile schema: FEDV, AEDV required; optional constraints, weights, taxonomy metadata."""
    # Required
    FEDV: list[float]  # length F, sum=1
    AEDV: list[float]  # length A, sum=1
    # Optional
    DENY_FAMILIES: list[int]
    ALLOW_FAMILIES: list[int]
    ALT_BAND: list[float]  # [min_alt, max_alt]
    ALT_TARGET: list[float]  # [mu_target, tau]
    MAX_AREA_DOMINANCE: float
    MAX_FAMILY_DOMINANCE: float
    MIN_AREA_SPREAD: float
    MIN_COVERAGE_RATIO: float
    w_family: float
    w_area: float
    w_forbid: float
    w_alt: float
    w_budget: float
    penalty_mode: str  # "linear" | "quadratic"
    profile_version: str
    profile_name: str
    # Taxonomy (canonical profiles must declare these)
    primary_axis: str  # distribution | concentration | altitude | constraint | regression
    strictness_level: str  # soft | medium | hard


def _normalize_weights(profile: StructureProfile) -> tuple[float, float, float, float, float]:
    """Return (w_family, w_area, w_forbid, w_alt, w_budget); default 1.0."""
    w_f = float(profile.get("w_family", 1.0))
    w_a = float(profile.get("w_area", 1.0))
    w_forbid = float(profile.get("w_forbid", 1.0))
    w_alt = float(profile.get("w_alt", 1.0))
    w_budget = float(profile.get("w_budget", 1.0))
    return (w_f, w_a, w_forbid, w_alt, w_budget)


# Tolerance for FEDV/AEDV sum check (deterministic)
_PROFILE_SUM_TOL = 1e-9


def validate_profile(profile: StructureProfile, F: int = 288, A: int = 12) -> None:
    """
    Validate profile shape and constraints. Raises ValueError on invalid data.
    Hard fail on violation; no warnings. FEDV/AEDV must sum to 1 within _PROFILE_SUM_TOL.
    """
    if "FEDV" not in profile or len(profile["FEDV"]) != F:
        raise ValueError(f"FEDV must be present and length F={F}")
    fedv = profile["FEDV"]
    if any(x < 0 for x in fedv):
        raise ValueError("FEDV entries must be non-negative")
    s_fedv = sum(fedv)
    if abs(s_fedv - 1.0) > _PROFILE_SUM_TOL:
        raise ValueError(f"FEDV must sum to 1 (got {s_fedv})")
    if "AEDV" not in profile or len(profile["AEDV"]) != A:
        raise ValueError(f"AEDV must be present and length A={A}")
    aedv = profile["AEDV"]
    if any(x < 0 for x in aedv):
        raise ValueError("AEDV entries must be non-negative")
    s_aedv = sum(aedv)
    if abs(s_aedv - 1.0) > _PROFILE_SUM_TOL:
        raise ValueError(f"AEDV must sum to 1 (got {s_aedv})")
    deny = set(profile.get("DENY_FAMILIES") or [])
    if deny and not all(0 <= f < F for f in deny):
        raise ValueError("DENY_FAMILIES must be subset of [0..F-1]")
    allow = set(profile.get("ALLOW_FAMILIES") or [])
    if allow and not all(0 <= f < F for f in allow):
        raise ValueError("ALLOW_FAMILIES must be subset of [0..F-1]")
    if deny and allow and (deny & allow):
        raise ValueError("DENY_FAMILIES and ALLOW_FAMILIES must be disjoint")
    band = profile.get("ALT_BAND")
    if band is not None:
        if len(band) != 2 or band[0] > band[1]:
            raise ValueError("ALT_BAND must be [min_alt, max_alt] with min <= max")
    alt_target = profile.get("ALT_TARGET")
    if alt_target is not None:
        if len(alt_target) != 2 or alt_target[1] < 0:
            raise ValueError("ALT_TARGET must be [mu_target, tau] with tau >= 0")
    for key in ("MAX_AREA_DOMINANCE", "MAX_FAMILY_DOMINANCE"):
        v = profile.get(key)
        if v is not None:
            if not isinstance(v, (int, float)):
                raise ValueError(f"{key} must be a number")
            if v < 0 or v > 1:
                raise ValueError(f"{key} must be in [0, 1] (got {v})")
    for key in ("MIN_AREA_SPREAD", "MIN_COVERAGE_RATIO"):
        v = profile.get(key)
        if v is not None:
            if not isinstance(v, (int, float)):
                raise ValueError(f"{key} must be a number")
            if v < 0 or v > 1:
                raise ValueError(f"{key} must be in [0, 1] (got {v})")
    if profile.get("penalty_mode") not in (None, "linear", "quadratic"):
        raise ValueError("penalty_mode must be 'linear' or 'quadratic' if present")
    # Taxonomy: when present, must be in allowed sets
    pa = profile.get("primary_axis")
    if pa is not None and pa not in PRIMARY_AXIS_VALUES:
        raise ValueError(f"primary_axis must be one of {sorted(PRIMARY_AXIS_VALUES)} (got {pa!r})")
    sl = profile.get("strictness_level")
    if sl is not None and sl not in STRICTNESS_LEVEL_VALUES:
        raise ValueError(f"strictness_level must be one of {sorted(STRICTNESS_LEVEL_VALUES)} (got {sl!r})")


def require_canonical_taxonomy(profile: StructureProfile) -> None:
    """
    Require primary_axis and strictness_level for canonical taxonomy profiles.
    Call after validate_profile() when the profile must belong to the canonical set.
    Raises ValueError if either field is missing or invalid.
    """
    if profile.get("primary_axis") is None:
        raise ValueError("Canonical profile must declare primary_axis")
    if profile.get("strictness_level") is None:
        raise ValueError("Canonical profile must declare strictness_level")


def profile_checksum(profile: StructureProfile) -> str:
    """Deterministic checksum of profile payload (keys sorted for consistency)."""
    canonical = json.dumps(profile, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def load_structure_profile(
    path: Path | str,
    F: int = 288,
    A: int = 12,
) -> tuple[StructureProfile, str]:
    """
    Load profile from JSON file. Returns (profile, checksum).
    Validates shape; raises ValueError on invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    profile = data if isinstance(data, dict) else data.get("profile", data)
    if not isinstance(profile, dict):
        raise ValueError("Profile must be a JSON object")
    validate_profile(profile, F=F, A=A)
    return profile, profile_checksum(profile)
