# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Engine 0.5.0 — Layer-1 (34_SPEC + 34_SPEC N1); “v0.4.x” = legacy SPEC-era label only.
25 variables base; when profile supplied, adds FPD, APD, FMP, ALTD, BVS, PCS.
Deterministic, input-bound. No LLM, no shadow, no books.
Inputs: total_tokens, matched list of (family_id, altitude), F, A, eps; optional profile_id, profile.
"""

from __future__ import annotations

import math
import time
from typing import Any

from core.contracts.layer_contract import LayerInput, LayerOutput
from .structure_profile import StructureProfile, profile_checksum, validate_profile

# Fixed normalization constants for profile deviation (deterministic per spec)
# Distance metric = L2 only; no future metric swapping. Valid when P and FEDV/Q and AEDV are valid distributions.
FPD_MAX = math.sqrt(2.0)  # max L2 distance between two probability vectors
APD_MAX = math.sqrt(2.0)
# Altitude domain frozen: 0.0 <= altitude <= 1.0 (global invariant)
ALT_MIN = 0.0
ALT_MAX = 1.0
ALT_NORM = ALT_MAX - ALT_MIN  # 1.0


def _hits_and_altitude_sum(
    matched: list[tuple[int, float]],
    F: int,
) -> tuple[list[int], list[float]]:
    """Build hits[f] and altitudeSum[f] from matched (familyGlobal, altitude)."""
    hits = [0] * F
    altitude_sum = [0.0] * F
    for fg, alt in matched:
        if 0 <= fg < F:
            hits[fg] += 1
            altitude_sum[fg] += alt
    return hits, altitude_sum


def _compute_gini(hits: list[int], total: float, eps: float) -> float:
    if total <= 0:
        return 0.0
    n = len(hits)
    sorted_hits = sorted(hits)
    return 1.0 - (2.0 / (n * total + eps)) * sum(
        (n - i) * sorted_hits[i] for i in range(n)
    )


def _second_max(hits: list[int]) -> int:
    M = max(hits) if hits else 0
    second = 0
    for h in hits:
        if h < M and h > second:
            second = h
    return second if second > 0 else M  # if all equal, secondMax = M (ratio 1.0)


def _area_hits(hits: list[int], F: int, A: int) -> list[int]:
    """Derive area_hits[a] from hits[f]. FAMILIES_PER_AREA = F // A."""
    if not A:
        return []
    fpa = F // A
    area_hits = [0] * A
    for f in range(F):
        if f < F and hits[f] > 0:
            a = f // fpa
            if a < A:
                area_hits[a] += hits[f]
    return area_hits


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _compute_profile_metrics(
    base: dict[str, Any],
    hits: list[int],
    altitude_sum: list[float],
    profile_id: str,
    profile: StructureProfile,
    F: int,
    A: int,
    eps: float,
) -> dict[str, Any]:
    """
    Compute 34_SPEC N1 profile metrics: FPD, APD, FMP, ALTD, BVS, PCS.
    Uses base L1 output for attributed, coverage, dominance, area_spread, etc.
    Zero-weight families (FEDV[f]=0) contribute to FPD normally; only DENY_FAMILIES defines hard prohibition.
    """
    attributed = base["ATTRIBUTED_TOKENS"]
    mean_altitude_global = base["MEAN_ALTITUDE_GLOBAL"]
    dominance_ratio = base["DOMINANCE_RATIO"]
    area_dominance_ratio = base["AREA_DOMINANCE_RATIO"]
    area_spread = base["AREA_SPREAD"]
    coverage = base["COVERAGE_RATIO"]

    FEDV = profile["FEDV"]
    AEDV = profile["AEDV"]
    deny = set(profile.get("DENY_FAMILIES") or [])

    # Deterministic empty case: attributed == 0 → FPD=1, APD=1, PCS=0 (no division-by-eps bias)
    if attributed == 0:
        out_empty: dict[str, Any] = {
            "PROFILE_MODE_ACTIVE": True,
            "PROFILE_ID": profile_id,
            "PROFILE_VERSION": profile.get("profile_version", ""),
            "PROFILE_CHECKSUM": profile_checksum(profile),
            "FAMILY_PROFILE_DEVIATION": 1.0,
            "AREA_PROFILE_DEVIATION": 1.0,
            "PROFILE_CONFORMANCE_SCORE": 0.0,
        }
        if deny:
            out_empty["FORBIDDEN_MASS_PENALTY"] = 0.0
        alt_band = profile.get("ALT_BAND")
        alt_target = profile.get("ALT_TARGET")
        if alt_band is not None or alt_target is not None:
            out_empty["ALTITUDE_DEVIATION"] = 1.0
        out_empty["BUDGET_VIOLATION_SCORE"] = 1.0 if any(
            profile.get(k) is not None for k in ("MAX_AREA_DOMINANCE", "MAX_FAMILY_DOMINANCE", "MIN_AREA_SPREAD", "MIN_COVERAGE_RATIO")
        ) else 0.0
        return out_empty

    area_hits = _area_hits(hits, F, A)
    denom = attributed + eps
    P = [hits[f] / denom for f in range(F)]
    Q = [area_hits[a] / denom for a in range(A)] if A else []

    # 7.1 Family Profile Deviation (L2 only; FEDV[f]=0 is not forbidden, contributes to FPD normally)
    fpd_raw = math.sqrt(sum((P[f] - FEDV[f]) ** 2 for f in range(F)))
    FPD = _clamp01(fpd_raw / FPD_MAX)

    # 7.2 Area Profile Deviation (L2 only)
    APD = 0.0
    if A and len(AEDV) == A:
        apd_raw = math.sqrt(sum((Q[a] - AEDV[a]) ** 2 for a in range(A)))
        APD = _clamp01(apd_raw / APD_MAX)

    # 7.3 Forbidden Mass Penalty
    FMP = 0.0
    if deny:
        fmp_raw = sum(hits[f] for f in deny if 0 <= f < F)
        FMP = fmp_raw / denom

    # 7.4 Altitude Deviation (altitude domain 0 ≤ alt ≤ 1 per invariant)
    ALTD = 0.0
    alt_band = profile.get("ALT_BAND")
    alt_target = profile.get("ALT_TARGET")
    if alt_band is not None and len(alt_band) == 2:
        lo, hi = alt_band[0], alt_band[1]
        if lo <= mean_altitude_global <= hi:
            ALTD = 0.0
        else:
            dist = (lo - mean_altitude_global) if mean_altitude_global < lo else (mean_altitude_global - hi)
            ALTD = _clamp01(dist / ALT_NORM)
    elif alt_target is not None and len(alt_target) == 2:
        mu_t, tau = alt_target[0], alt_target[1]
        if abs(mean_altitude_global - mu_t) <= tau:
            ALTD = 0.0
        else:
            dist = abs(mean_altitude_global - mu_t) - tau
            ALTD = _clamp01(dist / (ALT_NORM + 1e-9))

    # 7.5 Budget Violation Score: max(v_i) — governance-grade; a single cap breach is not diluted
    violations: list[float] = []
    if "MAX_AREA_DOMINANCE" in profile and profile["MAX_AREA_DOMINANCE"] is not None:
        cap = profile["MAX_AREA_DOMINANCE"]
        v = max(0.0, area_dominance_ratio - cap) / (1.0 - cap + eps)
        violations.append(min(1.0, v))
    if "MAX_FAMILY_DOMINANCE" in profile and profile["MAX_FAMILY_DOMINANCE"] is not None:
        cap = profile["MAX_FAMILY_DOMINANCE"]
        v = max(0.0, dominance_ratio - cap) / (1.0 - cap + eps)
        violations.append(min(1.0, v))
    if "MIN_AREA_SPREAD" in profile and profile["MIN_AREA_SPREAD"] is not None:
        floor = profile["MIN_AREA_SPREAD"]
        v = max(0.0, floor - area_spread) / (floor + eps)
        violations.append(min(1.0, v))
    if "MIN_COVERAGE_RATIO" in profile and profile["MIN_COVERAGE_RATIO"] is not None:
        floor = profile["MIN_COVERAGE_RATIO"]
        v = max(0.0, floor - coverage) / (floor + eps)
        violations.append(min(1.0, v))
    BVS = _clamp01(max(violations)) if violations else 0.0

    # 7.6 Profile Conformance Score
    w_f, w_a, w_forbid, w_alt, w_budget = (
        float(profile.get("w_family", 1.0)),
        float(profile.get("w_area", 1.0)),
        float(profile.get("w_forbid", 1.0)),
        float(profile.get("w_alt", 1.0)),
        float(profile.get("w_budget", 1.0)),
    )
    pen = w_f * FPD + w_a * APD
    weight_sum = w_f + w_a
    if deny:
        pen += w_forbid * FMP
        weight_sum += w_forbid
    if alt_band is not None or alt_target is not None:
        pen += w_alt * ALTD
        weight_sum += w_alt
    if violations:
        pen += w_budget * BVS
        weight_sum += w_budget
    PCS = 1.0 - _clamp01(pen / (weight_sum + eps))

    out: dict[str, Any] = {
        "PROFILE_MODE_ACTIVE": True,
        "PROFILE_ID": profile_id,
        "PROFILE_VERSION": profile.get("profile_version", ""),
        "PROFILE_CHECKSUM": profile_checksum(profile),
        "FAMILY_PROFILE_DEVIATION": FPD,
        "AREA_PROFILE_DEVIATION": APD,
        "PROFILE_CONFORMANCE_SCORE": PCS,
    }
    if deny:
        out["FORBIDDEN_MASS_PENALTY"] = FMP
    if alt_band is not None or alt_target is not None:
        out["ALTITUDE_DEVIATION"] = ALTD
    if violations:
        out["BUDGET_VIOLATION_SCORE"] = BVS
    return out


def compute_L1(
    total_tokens: int,
    matched: list[tuple[int, float]],
    F: int = 288,
    A: int = 12,
    eps: float = 1e-9,
    profile_id: str | None = None,
    profile: StructureProfile | None = None,
) -> dict[str, Any]:
    """
    Compute Layer-1 25 variables (34_SPEC). If profile_id and profile are supplied,
    also compute profile metrics (FPD, APD, FMP, ALTD, BVS, PCS) per 34_SPEC N1.
    matched = list of (familyGlobal, altitude) per attributed token.
    Returns dict with 34_SPEC keys; when profile present, adds PROFILE_ID, FAMILY_PROFILE_DEVIATION, etc.
    """
    if profile is not None and profile_id is None:
        profile_id = profile.get("profile_name") or profile.get("profile_version") or "profile"
    elif profile_id is None:
        profile_id = ""

    FAMILIES_PER_AREA = F // A if A else 24
    hits, altitude_sum = _hits_and_altitude_sum(matched, F)

    attributed = sum(hits)
    coverage = (attributed / total_tokens) if total_tokens > 0 else 0.0
    unique_families = sum(1 for h in hits if h > 0)
    family_activation_density = unique_families / F if F else 0.0
    l2_sum = sum(h * h for h in hits)
    family_hit_l2 = math.sqrt(l2_sum)

    max_hits = max(hits) if hits else 0
    dominant_family = 0
    for f in range(F):
        if hits[f] == max_hits:
            dominant_family = f
            break
    dominant_area = dominant_family // FAMILIES_PER_AREA

    dominance_ratio = max_hits / (attributed + eps)
    alt_sum_global = sum(altitude_sum)
    mean_altitude_global = alt_sum_global / (attributed + eps)
    mean_altitude_dominant = (
        altitude_sum[dominant_family] / (hits[dominant_family] + eps)
        if hits[dominant_family] > 0
        else 0.0
    )

    mu = mean_altitude_global
    var_sum = 0.0
    for f in range(F):
        if hits[f] > 0:
            mf = altitude_sum[f] / (hits[f] + eps)
            var_sum += hits[f] * (mf - mu) * (mf - mu)
    altitude_variance_global = var_sum / (attributed + eps)

    family_entropy = 0.0
    for f in range(F):
        p = hits[f] / (attributed + eps)
        if p > 0:
            family_entropy -= p * math.log(p)
    log_F = math.log(F) if F > 1 else 1.0
    normalized_family_entropy = min(1.0, family_entropy / log_F) if F > 1 else 0.0

    gini = _compute_gini(hits, float(attributed), eps)
    unique_areas = len({f // FAMILIES_PER_AREA for f in range(F) if hits[f] > 0})
    area_spread = unique_areas / A if A else 0.0
    hits_in_dominant_area = sum(
        hits[f] for f in range(F) if f // FAMILIES_PER_AREA == dominant_area
    )
    area_dominance_ratio = hits_in_dominant_area / (attributed + eps)
    second_max_hits = _second_max(hits)
    secondary_family_ratio = second_max_hits / (max_hits + eps)
    remainder = attributed - max_hits
    signal_to_noise = max_hits / (remainder + eps) if remainder >= 0 else 0.0
    sparsity_index = 1.0 - family_activation_density
    token_redundancy = (
        1.0 - (unique_families / (attributed + eps)) if attributed else 0.0
    )
    altitude_weighted_mass = sum(
        hits[f] * (altitude_sum[f] / (hits[f] + eps))
        for f in range(F)
        if hits[f] > 0
    )
    structural_stability = dominance_ratio * (1.0 - normalized_family_entropy)

    # PROFILE_MODE_ACTIVE set explicitly from input; never infer from PCS presence
    result: dict[str, Any] = {
        "PROFILE_MODE_ACTIVE": profile is not None,
        "TOTAL_TOKENS": total_tokens,
        "ATTRIBUTED_TOKENS": attributed,
        "COVERAGE_RATIO": coverage,
        "UNIQUE_FAMILIES_HIT": unique_families,
        "FAMILY_ACTIVATION_DENSITY": family_activation_density,
        "FAMILY_HIT_VECTOR_L1": float(attributed),
        "FAMILY_HIT_VECTOR_L2": family_hit_l2,
        "MAX_FAMILY_HITS": max_hits,
        "DOMINANT_FAMILY_ID": dominant_family,
        "DOMINANT_AREA_ID": dominant_area,
        "DOMINANCE_RATIO": dominance_ratio,
        "MEAN_ALTITUDE_GLOBAL": mean_altitude_global,
        "MEAN_ALTITUDE_DOMINANT": mean_altitude_dominant,
        "ALTITUDE_VARIANCE_GLOBAL": altitude_variance_global,
        "FAMILY_ENTROPY": family_entropy,
        "NORMALIZED_FAMILY_ENTROPY": normalized_family_entropy,
        "GINI_COEFFICIENT": gini,
        "UNIQUE_AREAS_HIT": unique_areas,
        "AREA_SPREAD": area_spread,
        "AREA_DOMINANCE_RATIO": area_dominance_ratio,
        "SECONDARY_FAMILY_RATIO": secondary_family_ratio,
        "SIGNAL_TO_NOISE_RATIO": signal_to_noise,
        "SPARSITY_INDEX": sparsity_index,
        "TOKEN_REDUNDANCY_RATIO": token_redundancy,
        "ALTITUDE_WEIGHTED_MASS": altitude_weighted_mass,
        "STRUCTURAL_STABILITY_INDEX": structural_stability,
    }
    if profile is not None:
        validate_profile(profile, F=F, A=A)
        result.update(
            _compute_profile_metrics(result, hits, altitude_sum, profile_id, profile, F, A, eps)
        )
    return result


def run(input: LayerInput) -> LayerOutput:
    """Layer-1 public entry point. Consumes LayerInput, returns LayerOutput. No other public entry points."""
    t0 = time.perf_counter()
    meta = input.metadata
    F = int(meta.get("F", 288))
    A = int(meta.get("A", 12))
    eps = float(meta.get("eps", 1e-9))
    matched = meta.get("matched", [])
    profile_id = meta.get("profile_id")
    profile = meta.get("profile")
    total_tokens = len(input.tokens)
    result = compute_L1(
        total_tokens,
        matched,
        F=F,
        A=A,
        eps=eps,
        profile_id=profile_id,
        profile=profile,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return LayerOutput(
        layer_id=1,
        result=result,
        diagnostics={"layer_id": 1, "execution_time_ms": round(elapsed_ms, 6)},
    )
