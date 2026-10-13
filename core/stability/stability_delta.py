# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA Δ (Delta) stability layer.
Non-destructive structural correction: analyzes pipeline state after L6 and produces
correction signals only. Never modifies previous layer outputs.
Deterministic: no randomness, no external state, only reads pipeline state.
"""

from __future__ import annotations

from typing import Any, Dict

# Anomaly type constants (for instability_flags)
ANOMALY_AREA_COLLISION = "AREA_COLLISION"
ANOMALY_FAMILY_DRIFT = "FAMILY_DRIFT"
ANOMALY_CURVATURE_SPIKE = "CURVATURE_SPIKE"
ANOMALY_PROPAGATION_LOOP = "PROPAGATION_LOOP"

# Thresholds (deterministic, fixed)
THRESHOLD_CROSS_AREA_RATIO = 0.50  # above this → area collision signal
THRESHOLD_LOOP_DENSITY = 0.20  # above this → propagation loop signal
THRESHOLD_CONDITION_NUMBER = 2.0  # L6 condition above this → curvature spike
THRESHOLD_CURVATURE = 0.50  # L6 curvature metrics above this → curvature spike
THRESHOLD_GLOBAL_STABILITY_LOW = 0.50  # L6 GLOBAL_STABILITY_SCORE below this → instability
ANOMALY_SCORE_THRESHOLD_LOW_CONFIDENCE = 0.50  # used by L7 for OUTPUT_TRUST_TAG


def run_stability(layers: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze L1–L6 state and return structural correction signals.
    Input: state.layers (at least 1–6). Output: diagnostics dict for state.diagnostics["stability"]
    and input.metadata["stability"]. Deterministic.
    """
    l1 = layers.get(1) or {}
    l2 = layers.get(2) or {}
    l6 = layers.get(6) or {}
    instability_flags: list[str] = []
    corrective_bias: Dict[str, Any] = {}

    # ---- AREA_COLLISION: dominant area vs traversal containment ----
    dom_area = int(l1.get("DOMINANT_AREA_ID", 0))
    cross_area_ratio = float(l2.get("CROSS_AREA_RATIO", 0.0))
    area_spread = float(l1.get("AREA_SPREAD", 0.0))
    if cross_area_ratio > THRESHOLD_CROSS_AREA_RATIO:
        instability_flags.append(ANOMALY_AREA_COLLISION)
    elif area_spread > 0.5 and cross_area_ratio > 0.3:
        instability_flags.append(ANOMALY_AREA_COLLISION)

    # ---- FAMILY_DRIFT: dominant family not in traversal ----
    dom_family = int(l1.get("DOMINANT_FAMILY_ID", 0))
    visited_ids = l2.get("VISITED_IDS") or []
    visited_set = set(visited_ids) if isinstance(visited_ids, list) else set()
    if visited_set and dom_family not in visited_set:
        instability_flags.append(ANOMALY_FAMILY_DRIFT)

    # ---- CURVATURE_SPIKE: L6 curvature / condition / consistency ----
    condition_num = float(l6.get("CONDITION_NUMBER", 1.0))
    dominance_curvature = float(l6.get("DOMINANCE_CURVATURE", 0.0))
    entropy_curvature = float(l6.get("ENTROPY_CURVATURE", 0.0))
    global_stability = float(l6.get("GLOBAL_STABILITY_SCORE", 1.0))
    if condition_num > THRESHOLD_CONDITION_NUMBER or dominance_curvature > THRESHOLD_CURVATURE or entropy_curvature > THRESHOLD_CURVATURE:
        instability_flags.append(ANOMALY_CURVATURE_SPIKE)
    if global_stability < THRESHOLD_GLOBAL_STABILITY_LOW:
        if ANOMALY_CURVATURE_SPIKE not in instability_flags:
            instability_flags.append(ANOMALY_CURVATURE_SPIKE)

    # ---- PROPAGATION_LOOP: L2 loop density ----
    loop_density = float(l2.get("LOOP_DENSITY", 0.0))
    loop_count = int(l2.get("LOOP_COUNT", 0))
    if loop_density > THRESHOLD_LOOP_DENSITY or loop_count > 2:
        instability_flags.append(ANOMALY_PROPAGATION_LOOP)

    # ---- Anomaly score: 0.0 (clean) to 1.0 (max anomaly), deterministic ----
    n_flags = len(instability_flags)
    anomaly_score = min(1.0, 0.28 * n_flags) if n_flags else 0.0

    # ---- Corrective bias (signals for L7) ----
    if anomaly_score >= ANOMALY_SCORE_THRESHOLD_LOW_CONFIDENCE:
        corrective_bias["trust_demotion"] = True
        corrective_bias["suggest_low_confidence_tag"] = True
    if ANOMALY_FAMILY_DRIFT in instability_flags:
        corrective_bias["dominant_family_in_traversal_check"] = False
    if ANOMALY_AREA_COLLISION in instability_flags:
        corrective_bias["area_containment_weakened"] = True

    # ---- Confidence adjustment: negative when anomaly high (L7 can reduce confidence) ----
    confidence_adjustment = -anomaly_score * 0.25  # in [-0.25, 0]

    return {
        "anomaly_score": round(anomaly_score, 6),
        "instability_flags": instability_flags,
        "corrective_bias": corrective_bias,
        "confidence_adjustment": round(confidence_adjustment, 6),
    }
