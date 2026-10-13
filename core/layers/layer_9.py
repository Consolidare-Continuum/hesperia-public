# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Engine 0.5.0 — Layer-9 (42_SPEC); “v0.4.x” = legacy SPEC-era label only.
25 variables: bands, pillars, BRAND_WORD_*, ACTION_* from L3, L4, L7, L8 SI_*.
Final layer: L1–L9 metrics become human-facing labels (no locale here; i18n can wrap L9 output).
"""

from __future__ import annotations

import time
from typing import Any

from core.contracts.layer_contract import LayerInput, LayerOutput


def _clamp(u: int | float, lo: int | float, hi: int | float) -> int:
    return max(int(lo), min(int(hi), int(u)))


def compute_L9(
    l3: dict[str, Any],
    l4: dict[str, Any],
    l7: dict[str, Any],
    l8: dict[str, Any],
    MAX_SHORTFALL: int = 2,
) -> dict[str, Any]:
    """Layer-9 25 variables (42_SPEC)."""
    si_coverage = l8["SI_COVERAGE_U1000"]
    si_dominance = l8["SI_DOMINANCE_U1000"]
    si_geometric = l8["SI_GEOMETRIC_STABILITY_U1000"]
    si_area_leakage = l8["SI_AREA_LEAKAGE_U1000"]
    si_entropy = l8["SI_ENTROPY_U1000"]
    si_evidence = l8["SI_EVIDENCE_SUPPORT_U1000"]
    si_contradiction = l8["SI_CONTRADICTION_PRESSURE_U1000"]
    si_global = l8["SI_GLOBAL_STABILITY_U1000"]
    si_confidence = l8["SI_SYSTEM_CONFIDENCE_U1000"]
    si_trig = l8["SI_TRIG_REALITY_FLAG"]

    u = si_confidence
    BAND_0_CRITICAL = u < 200
    BAND_1_WEAK = 200 <= u < 400
    BAND_2_FAIR = 400 <= u < 600
    BAND_3_GOOD = 600 <= u < 800
    BAND_4_STRONG = 800 <= u < 950
    BAND_5_EXCELLENT = u >= 950

    AREA_CONTAINMENT_U1000 = _clamp(1000 - si_area_leakage, 0, 1000)
    CONSISTENCY_U1000 = _clamp(1000 - si_contradiction, 0, 1000)
    PILLAR_INPUT_QUALITY_U1000 = _clamp(round(0.60 * si_coverage + 0.40 * si_dominance), 0, 1000)
    PILLAR_GEOMETRY_U1000 = _clamp(round(0.70 * si_geometric + 0.30 * AREA_CONTAINMENT_U1000), 0, 1000)
    PILLAR_EVIDENCE_U1000 = si_evidence
    PILLAR_CONSISTENCY_U1000 = _clamp(round(0.60 * CONSISTENCY_U1000 + 0.40 * (1000 - si_entropy)), 0, 1000)
    PILLAR_STABILITY_U1000 = si_global
    PILLAR_GOVERNANCE_U1000 = 1000 if l7["DECISION_STATUS_CODE"] == 0 else _clamp(1000 - 10 * l7["DECISION_STATUS_CODE"], 0, 1000)

    BRAND_WORD_TRUST = (
        "BLOCKED" if l7["DECISION_STATUS_CODE"] != 0 else
        "TRUSTED" if si_confidence >= 850 else
        "USABLE" if si_confidence >= 650 else
        "TENTATIVE" if si_confidence >= 450 else "FRAGILE"
    )
    BRAND_WORD_EVIDENCE = "SUPPORTED" if si_evidence >= 800 else "BACKED" if si_evidence >= 600 else "THIN" if si_evidence >= 400 else "UNSUPPORTED"
    BRAND_WORD_CONTRADICTION = "CONSISTENT" if CONSISTENCY_U1000 >= 800 else "MIXED" if CONSISTENCY_U1000 >= 600 else "CONTESTED" if CONSISTENCY_U1000 >= 400 else "CONTRADICTED"
    BRAND_WORD_GEOMETRY = "CONTAINED" if PILLAR_GEOMETRY_U1000 >= 800 else "STABLE" if PILLAR_GEOMETRY_U1000 >= 600 else "DIFFUSE" if PILLAR_GEOMETRY_U1000 >= 400 else "CHAOTIC"
    BRAND_WORD_SHADOW = (
        "OFF" if not l3["SHADOW_ENABLED"] else
        "REJECTED" if not l3["SHADOW_ACCEPTABILITY_GATE"] else
        "JUSTIFIED" if l7["SHADOW_JUSTIFICATION_SCORE"] > 0.0 else "NEUTRAL"
    )

    ACTION_REQUIRE_MORE_INPUT = si_coverage < 500
    ACTION_REQUIRE_EVIDENCE_REBUILD = l4["INTEGRITY_CHECK_PASS_RATIO"] < 1.0 or l4["RETRIEVAL_SHORTFALL_BASELINE"] > MAX_SHORTFALL
    ACTION_REQUIRE_GOVERNANCE_REVIEW = l7["DECISION_STATUS_CODE"] != 0 or si_confidence < 450
    ACTION_ALLOW_HUMAN_SUMMARY = l7["DECISION_STATUS_CODE"] == 0 and si_confidence >= 650 and si_trig

    return {
        "BAND_0_CRITICAL": BAND_0_CRITICAL,
        "BAND_1_WEAK": BAND_1_WEAK,
        "BAND_2_FAIR": BAND_2_FAIR,
        "BAND_3_GOOD": BAND_3_GOOD,
        "BAND_4_STRONG": BAND_4_STRONG,
        "BAND_5_EXCELLENT": BAND_5_EXCELLENT,
        "DIRECTIONALIZE_HIGH_IS_GOOD": "clamp(u,0,1000)",
        "DIRECTIONALIZE_LOW_IS_GOOD": "1000-clamp(u,0,1000)",
        "AREA_CONTAINMENT_U1000": AREA_CONTAINMENT_U1000,
        "CONSISTENCY_U1000": CONSISTENCY_U1000,
        "PILLAR_INPUT_QUALITY_U1000": PILLAR_INPUT_QUALITY_U1000,
        "PILLAR_GEOMETRY_U1000": PILLAR_GEOMETRY_U1000,
        "PILLAR_EVIDENCE_U1000": PILLAR_EVIDENCE_U1000,
        "PILLAR_CONSISTENCY_U1000": PILLAR_CONSISTENCY_U1000,
        "PILLAR_STABILITY_U1000": PILLAR_STABILITY_U1000,
        "PILLAR_GOVERNANCE_U1000": PILLAR_GOVERNANCE_U1000,
        "BRAND_WORD_TRUST": BRAND_WORD_TRUST,
        "BRAND_WORD_EVIDENCE": BRAND_WORD_EVIDENCE,
        "BRAND_WORD_CONTRADICTION": BRAND_WORD_CONTRADICTION,
        "BRAND_WORD_GEOMETRY": BRAND_WORD_GEOMETRY,
        "BRAND_WORD_SHADOW": BRAND_WORD_SHADOW,
        "ACTION_REQUIRE_MORE_INPUT": ACTION_REQUIRE_MORE_INPUT,
        "ACTION_REQUIRE_EVIDENCE_REBUILD": ACTION_REQUIRE_EVIDENCE_REBUILD,
        "ACTION_REQUIRE_GOVERNANCE_REVIEW": ACTION_REQUIRE_GOVERNANCE_REVIEW,
        "ACTION_ALLOW_HUMAN_SUMMARY": ACTION_ALLOW_HUMAN_SUMMARY,
    }


def run(input: LayerInput) -> LayerOutput:
    """Layer-9 public entry point. Consumes LayerInput, returns LayerOutput. No other public entry points."""
    t0 = time.perf_counter()
    meta = input.metadata
    layers = meta.get("layers", {})
    l3 = layers.get(3)
    l4 = layers.get(4)
    l7 = layers.get(7)
    l8 = layers.get(8)
    if not all([l3, l4, l7, l8]):
        raise ValueError("Layer 9 requires layers 3, 4, 7, 8 results in input.metadata['layers']")
    defaults = meta.get("defaults", {})
    result = compute_L9(
        l3, l4, l7, l8,
        MAX_SHORTFALL=defaults.get("MAX_SHORTFALL", 2),
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return LayerOutput(
        layer_id=9,
        result=result,
        diagnostics={"layer_id": 9, "execution_time_ms": round(elapsed_ms, 6)},
    )
