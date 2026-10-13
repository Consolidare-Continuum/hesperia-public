# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

# Map L1–L9 outputs to R1–R4 Unit schema. Ref: schema/Unit.schema.json, Part C.
#
# Notes (spec alignment):
# - Empty unit (token_count==0): fixed SI, band=spiky, decision_code=INVALID_EMPTY_UNIT; no guards.
# - Coverage/leakage from TopN: coverage = sum(p_f), leakage = 1 - coverage; coverage+leakage == 1.
# - consistency = 1 - entropy; if coverage==0 then consistency=0 (input_signal gate).
# - Trust tier: T0 if token_count<12; T3 if token_count>=60 and shadow<=0.35 and leakage<=0.40 and entropy<=0.70; else T2.
# - Band: if coverage==0 → spiky (hard override). Else T0→spiky; then coherent/fragmented/stable from SI.
# - Decision: no top_families → ATTR_FAIL_NO_FAMILIES; SIGMA_FAIL_LEAK only if leakage>0.75 and token_count>=12.
#
from __future__ import annotations

from typing import Any

from core.propagation.r1_r4_esm_defaults import get_top_n


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _top_families_from_hits(hits: list[int], top_n: int, F: int, eps: float = 1e-9) -> list[dict[str, Any]]:
    """Build top_families list: family_id F1..F288, coverage, rank. Tie-break by family_id ascending."""
    total = sum(hits)
    if total <= 0:
        return []
    order = sorted(range(F), key=lambda f: (-hits[f], f))
    out = []
    for rank, f in enumerate(order[:top_n], 1):
        if hits[f] <= 0:
            break
        coverage = _clamp01(hits[f] / (total + eps))
        out.append({"family_id": f"F{f + 1}", "coverage": round(coverage, 6), "rank": rank})
    return out


def _top_areas_from_hits(hits: list[int], F: int, A: int, top_n: int = 12, eps: float = 1e-9) -> list[dict[str, Any]]:
    """Aggregate hits by area; return top areas as area_id A1..A12, coverage, rank."""
    if not A:
        return []
    fpa = F // A
    area_hits = [0] * A
    for f in range(F):
        if 0 <= f < F and hits[f] > 0:
            a = f // fpa
            if a < A:
                area_hits[a] += hits[f]
    total = sum(area_hits)
    if total <= 0:
        return []
    order = sorted(range(A), key=lambda a: (-area_hits[a], a))
    out = []
    for rank, a in enumerate(order[:top_n], 1):
        if area_hits[a] <= 0:
            break
        coverage = _clamp01(area_hits[a] / (total + eps))
        out.append({"area_id": f"A{a + 1}", "coverage": round(coverage, 6), "rank": rank})
    return out


def _si_metrics_from_layers(
    l1: dict[str, Any],
    l3: dict[str, Any],
    l5: dict[str, Any],
    l6: dict[str, Any],
    l7: dict[str, Any],
    *,
    token_count: int,
    top_families: list[dict[str, Any]],
    coverage_override: float | None = None,
    leakage_override: float | None = None,
) -> dict[str, Any]:
    """Build SI_metrics dict for Unit schema (all [0,1], trust_tier T0–T3).
    When token_count==0 returns fixed empty-unit SI; no guards run.
    Coverage/leakage from TopN: coverage = sum(p_f for f in TopN), leakage = 1 - coverage.
    Trust tier: T0 if token_count < 12; T3 only if token_count >= 60 and shadow_deviation <= 0.35; else T1/T2.
    Stability = 1 - entropy (locked).
    """
    if token_count == 0:
        return {
            "coverage": 0.0,
            "dominance": 0.0,
            "entropy": 0.0,
            "leakage": 1.0,
            "contradiction_pressure": 0.0,
            "consistency": 0.0,
            "shadow_deviation": 0.0,
            "trust_tier": "T0",
        }
    dominance = _clamp01(l1.get("DOMINANCE_RATIO", 0.0))
    entropy = _clamp01(l1.get("NORMALIZED_FAMILY_ENTROPY", 0.0))
    if coverage_override is not None and leakage_override is not None:
        coverage = _clamp01(coverage_override)
        leakage = _clamp01(leakage_override)
    else:
        coverage = _clamp01(sum(tf.get("coverage", 0.0) for tf in top_families))
        leakage = _clamp01(1.0 - coverage)
    err = abs((coverage + leakage) - 1.0)
    if err >= 1e-6:
        raise AssertionError(f"coverage + leakage != 1 (err={err})")
    contradiction_pressure = _clamp01(l5.get("CONTRADICTION_PRESSURE_SCORE", 0.0))
    # Signal gate: consistency = 0 when coverage == 0 (no "perfect consistency" on empty attribution)
    if coverage <= 0:
        stability = 0.0
    else:
        stability = _clamp01(1.0 - entropy)
        if abs(stability - (1.0 - entropy)) >= 1e-6:
            raise AssertionError(f"stability must equal 1 - entropy (stability={stability}, entropy={entropy})")
    shadow_deviation = _clamp01(l3.get("SHADOW_DEVIATION_SCORE", 0.0))
    # Trust tier: same rule for all R-levels. T0 if <12; T3 if >=60 and shadow/leakage/entropy within bounds; else T2 (T1 when shadow missing)
    if token_count < 12:
        trust_tier = "T0"
    elif token_count >= 60 and shadow_deviation <= 0.35 and leakage <= 0.40 and entropy <= 0.70:
        trust_tier = "T3"
    else:
        trust_tier = "T2"
    return {
        "coverage": round(coverage, 6),
        "dominance": round(dominance, 6),
        "entropy": round(entropy, 6),
        "leakage": round(leakage, 6),
        "contradiction_pressure": round(contradiction_pressure, 6),
        "consistency": round(stability, 6),
        "shadow_deviation": round(shadow_deviation, 6),
        "trust_tier": trust_tier,
    }


def _band_from_si(si: dict[str, Any]) -> str:
    """Band from SI_metrics per spec B.9: spiky | fragmented | coherent | stable.
    Hard override: coverage == 0 → spiky (no-attribution units cannot be stable).
    """
    if si.get("coverage", 0.0) == 0:
        return "spiky"
    tt = si.get("trust_tier", "T2")
    if tt == "T0":
        return "spiky"
    entropy = si.get("entropy", 0.0)
    dominance = si.get("dominance", 0.0)
    leakage = si.get("leakage", 0.0)
    if entropy > 0.6 and dominance < 0.4:
        return "fragmented"
    if dominance > 0.55 and leakage < 0.15 and entropy < 0.35:
        return "coherent"
    return "stable"


def _decision_code_from_l7(
    l7: dict[str, Any],
    *,
    token_count: int,
    top_families: list[dict[str, Any]],
    leakage: float,
    leak_fail_threshold: float = 0.75,
    t_min_valid: int = 12,
) -> str:
    """Decision code: ATTR_FAIL_NO_FAMILIES when no matches; SIGMA_FAIL_LEAK only when leakage > threshold and token_count >= T_min."""
    if token_count > 0 and not top_families:
        return "ATTR_FAIL_NO_FAMILIES"
    code = int(l7.get("DECISION_STATUS_CODE", 0))
    if code == 0:
        return "OK"
    if code == 75:
        return "GAMMA_DRIFT"  # profile conformance
    if code == 10:  # L7 leak gate
        if leakage > leak_fail_threshold and token_count >= t_min_valid:
            return "SIGMA_FAIL_LEAK"
        return "OK"  # leak not applicable below threshold / T_min
    if code == 20:
        return "SIGMA_FAIL_ENTROPY"
    if code in (30, 40, 50, 60, 70):
        return "GAMMA_DRIFT"
    return "GAMMA_DRIFT"


def build_unit(
    unit_id: str,
    level: str,
    parent_id: str | None,
    token_count: int,
    hits: list[int],
    l1: dict[str, Any],
    l2: dict[str, Any],
    l3: dict[str, Any],
    l4: dict[str, Any],
    l5: dict[str, Any],
    l6: dict[str, Any],
    l7: dict[str, Any],
    F: int = 288,
    A: int = 12,
    top_n: int | None = None,
) -> dict[str, Any]:
    """Build a Unit dict conforming to schema/Unit.schema.json from L1–L7 and hits.
    When token_count==0 returns fixed SI (no guards); decision_code INVALID_EMPTY_UNIT.
    """
    if top_n is None:
        top_n = get_top_n()
    top_families = _top_families_from_hits(hits, top_n, F)
    top_areas = _top_areas_from_hits(hits, F, A, top_n=12)
    if token_count == 0:
        si = _si_metrics_from_layers(l1, l3, l5, l6, l7, token_count=0, top_families=[])
        band = "spiky"
        decision_code = "INVALID_EMPTY_UNIT"
    else:
        coverage_si = _clamp01(sum(tf.get("coverage", 0.0) for tf in top_families))
        leakage_si = _clamp01(1.0 - coverage_si)
        si = _si_metrics_from_layers(
            l1, l3, l5, l6, l7,
            token_count=token_count,
            top_families=top_families,
            coverage_override=coverage_si,
            leakage_override=leakage_si,
        )
        band = _band_from_si(si)
        decision_code = _decision_code_from_l7(
            l7,
            token_count=token_count,
            top_families=top_families,
            leakage=si.get("leakage", 0.0),
        )
    return {
        "unit_id": unit_id,
        "level": level,
        "parent_id": parent_id,
        "token_count": token_count,
        "top_areas": top_areas,
        "top_families": top_families,
        "SI_metrics": si,
        "flags": {"band": band, "decision_code": decision_code},
    }
