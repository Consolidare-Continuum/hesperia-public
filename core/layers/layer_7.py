# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Engine 0.5.0 — Layer-7 (40_SPEC); “v0.4.x” = legacy SPEC-era label only.
25 variables: consistency gates, limits, alignment, SYSTEM_CONFIDENCE_SCORE, DECISION_STATUS_CODE, OUTPUT_TRUST_TAG.
Consumes L1..L6; downstream: L8 (SI_SYSTEM_CONFIDENCE), L9 (pillars, BRAND_WORD_*, ACTION_*).
Decision code 75 = PROFILE_CONFORMANCE_FAILURE (34_SPEC N1); reserved permanently.
"""
from __future__ import annotations

import time
from typing import Any

from core.contracts.layer_contract import LayerInput, LayerOutput
from core.stability.stability_delta import ANOMALY_SCORE_THRESHOLD_LOW_CONFIDENCE

# Decision registry: 75 → PROFILE_CONFORMANCE_FAILURE (never reuse)
DECISION_CODE_PROFILE_CONFORMANCE_FAILURE = 75

def _c(x, lo, hi): return max(lo, min(hi, x))

def compute_L7(l1,l2,l3,l4,l5,l6,visited_B=None,F=288,A=12,MIN_COVERAGE_RATIO=0.10,EPS_INT=1e-6,SHADOW_MAX_DEVIATION=0.25,MAX_CONTRADICTION=0.50,MAX_CROSS_AREA_RATIO=0.50,MAX_LYAPUNOV=2.0,HIGH_CONF=0.70,MED_CONF=0.40,EVIDENCE_SUPPORT_INDEX_SHADOW=0.0,MIN_PCS=0.0):
    FPA=F//A if A else 24
    visited_B=visited_B or set(l2.get("VISITED_IDS",[]))
    g1=l1["COVERAGE_RATIO"]>=MIN_COVERAGE_RATIO
    # Profile conformance: use PROFILE_MODE_ACTIVE only (never infer from PCS presence)
    profile_mode_active = l1.get("PROFILE_MODE_ACTIVE") is True
    g1p = (not profile_mode_active or l1["PROFILE_CONFORMANCE_SCORE"] >= MIN_PCS) if (MIN_PCS > 0 and profile_mode_active) else True
    g2=abs(l1["FAMILY_HIT_VECTOR_L1"]-l1["ATTRIBUTED_TOKENS"])<=EPS_INT
    g3=(l1["ATTRIBUTED_TOKENS"]==0 and l2["TOTAL_REACHABLE_NODES"]==0)or(l1["ATTRIBUTED_TOKENS"]>0 and l2["TOTAL_REACHABLE_NODES"]>0)
    g4=l1["DOMINANT_FAMILY_ID"] in visited_B
    g5=l1["DOMINANT_AREA_ID"]==(l1["DOMINANT_FAMILY_ID"]//FPA)
    g6=l4["INTEGRITY_CHECK_PASS_RATIO"]==1.0
    g7=(not l3["SHADOW_ENABLED"] and l3["SHADOW_DEVIATION_SCORE"]==0.0)or l3["SHADOW_ENABLED"]
    g8=l5["REALITY_GATE_TRIG"]
    g9=l5["REALITY_GATE_COUNTER_EVIDENCE"]
    lyap=l6.get("LYAPUNOV_ESTIMATE",0.0)
    g10=lyap==lyap and abs(lyap)!=float("inf")
    tier=0 if not g1 else 1 if not g6 else 2 if not g8 else 3
    shadow_ok=l3["SHADOW_ACCEPTABILITY_GATE"]
    contrad_ok=l5["CONTRADICTION_PRESSURE_SCORE"]<=MAX_CONTRADICTION
    area_ok=l2["CROSS_AREA_RATIO"]<=MAX_CROSS_AREA_RATIO
    align=0.60*l4["EVIDENCE_SUPPORT_INDEX_BASELINE"]+0.40*l2["GEOMETRIC_STABILITY_INDEX"]
    delta_shadow=EVIDENCE_SUPPORT_INDEX_SHADOW-l4["EVIDENCE_SUPPORT_INDEX_BASELINE"]
    just=(1.0 if shadow_ok else 0.0)*max(0.0,delta_shadow)*(1.0-l3["SHADOW_DEVIATION_SCORE"])
    supp=_c(l4["EVIDENCE_SUPPORT_INDEX_BASELINE"]*(1.0-l5["CONTRADICTION_PRESSURE_SCORE"]),0.0,1.0)
    conf=_c((tier/3.0)*l1["STRUCTURAL_STABILITY_INDEX"]*l2["GEOMETRIC_STABILITY_INDEX"]*supp*l6["GLOBAL_STABILITY_SCORE"],0.0,1.0)
    code=DECISION_CODE_PROFILE_CONFORMANCE_FAILURE if (MIN_PCS>0 and profile_mode_active and not g1p) else 10 if not g1 else 20 if not g6 else 30 if not area_ok else 40 if not shadow_ok else 50 if not contrad_ok else 60 if not g8 else 70 if lyap>MAX_LYAPUNOV else 0
    tag="HIGH" if code==0 and conf>=HIGH_CONF else "MED" if code==0 and conf>=MED_CONF else "LOW"
    out={"CONSIST_COVERAGE_MIN_GATE":g1,"CONSIST_ATTRIBUTION_MASS_EQUALITY":g2,"CONSIST_TRAVERSAL_NONEMPTY_WHEN_ATTRIBUTED":g3,"CONSIST_DOMINANT_FAMILY_IN_TRAVERSAL":g4,"CONSIST_AREA_MAPPING":g5,"CONSIST_EVIDENCE_INTEGRITY_HARD":g6,"CONSIST_SHADOW_DELTA_ONLY_IF_SHADOW":g7,"CONSIST_TRIG_REQUIRED_FOR_ANGLE_METRICS":g8,"CONSIST_COUNTER_EVIDENCE_VALID":g9,"CONSIST_STABILITY_REGIME_VALID":g10,"TRUST_TIER":tier,"MAX_ALLOWABLE_SHADOW_DEVIATION":SHADOW_MAX_DEVIATION,"SHADOW_WITHIN_LIMITS":shadow_ok,"MAX_ALLOWABLE_CONTRADICTION":MAX_CONTRADICTION,"CONTRADICTION_WITHIN_LIMITS":contrad_ok,"MAX_AREA_LEAKAGE":MAX_CROSS_AREA_RATIO,"AREA_LEAKAGE_WITHIN_LIMITS":area_ok,"MAX_CHAOS_LEVEL":MAX_LYAPUNOV,"STRUCTURE_EVIDENCE_ALIGNMENT":align,"SHADOW_EVIDENCE_ALIGNMENT_DELTA":delta_shadow,"SHADOW_JUSTIFICATION_SCORE":just,"CONTRADICTION_ADJUSTED_SUPPORT":supp,"SYSTEM_CONFIDENCE_SCORE":conf,"DECISION_STATUS_CODE":code,"OUTPUT_TRUST_TAG":tag}
    if profile_mode_active:
        out["CONSIST_PROFILE_CONFORMANCE"] = g1p
        # Log profile checksum in decision trace (L7)
        if l1.get("PROFILE_CHECKSUM") is not None:
            out["PROFILE_CHECKSUM"] = l1["PROFILE_CHECKSUM"]
    return out


def run(input: LayerInput) -> LayerOutput:
    """Layer-7 public entry point. Consumes LayerInput, returns LayerOutput. No other public entry points."""
    t0 = time.perf_counter()
    meta = input.metadata
    layers = meta.get("layers", {})
    l1, l2, l3, l4, l5, l6 = layers.get(1), layers.get(2), layers.get(3), layers.get(4), layers.get(5), layers.get(6)
    if not all([l1, l2, l3, l4, l5, l6]):
        raise ValueError("Layer 7 requires layers 1–6 results in input.metadata['layers']")
    visited_B = meta.get("visited_B")
    if visited_B is None:
        visited_B = set(l2.get("VISITED_IDS", []))
    F = int(meta.get("F", 288))
    A = int(meta.get("A", 12))
    defaults = meta.get("defaults", {})
    result = compute_L7(
        l1, l2, l3, l4, l5, l6,
        visited_B=visited_B,
        F=F,
        A=A,
        **{k: defaults.get(k) for k in ("MIN_COVERAGE_RATIO", "MAX_CROSS_AREA_RATIO", "MAX_LYAPUNOV", "HIGH_CONF", "MED_CONF", "MIN_PCS") if k in defaults},
    )
    # Δ consistency layer: optionally demote OUTPUT_TRUST_TAG when structural anomaly score is high
    stability = meta.get("stability")
    if isinstance(stability, dict):
        anomaly_score = float(stability.get("anomaly_score", 0.0))
        if anomaly_score > ANOMALY_SCORE_THRESHOLD_LOW_CONFIDENCE:
            result["OUTPUT_TRUST_TAG"] = "LOW_CONFIDENCE"
            result["STABILITY_ANOMALY_SCORE"] = anomaly_score
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return LayerOutput(
        layer_id=7,
        result=result,
        diagnostics={"layer_id": 7, "execution_time_ms": round(elapsed_ms, 6)},
    )
