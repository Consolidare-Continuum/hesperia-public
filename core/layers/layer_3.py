# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Engine 0.5.0 — Layer-3 (36_SPEC); “v0.4.x” = legacy SPEC-era label only.
25 variables: comparison of baseline (B) vs shadow (S) runs. Deterministic.
Inputs: L1_B, L2_B, hits_B, L1_S, L2_S, hits_S, F, A, governance params, eps. Downstream: L4, L7, L8.
"""

from __future__ import annotations

import math
import time
from typing import Any

from core.contracts.layer_contract import LayerInput, LayerOutput


def _top_k_families(hits: list[int], F: int, K: int) -> set[int]:
    """Families with top K hit counts; tie-break by hits desc then family id asc."""
    indexed = [(hits[f], f) for f in range(min(F, len(hits)))]
    indexed.sort(key=lambda x: (-x[0], x[1]))
    return {idx[1] for idx in indexed[:K]}


def compute_L3(
    l1_B: dict[str, Any],
    l2_B: dict[str, Any],
    hits_B: list[int],
    l1_S: dict[str, Any],
    l2_S: dict[str, Any],
    hits_S: list[int],
    F: int = 288,
    A: int = 12,
    SHADOW_MAX_DEVIATION: float = 0.25,
    SHADOW_MAX_CROSS_AREA_DELTA: float = 0.10,
    SHADOW_ALLOW_AREA_FLIP: bool = False,
    TOP_K: int = 10,
    eps: float = 1e-12,
) -> dict[str, Any]:
    """
    Compute Layer-3 25 variables (36_SPEC).
    Requires both B and S runs (L1+L2 each). VISITED_IDS from L2 used for Jaccard/symmetric difference.
    """
    FPA = F // A if A else 24
    dominant_family_B = int(l1_B["DOMINANT_FAMILY_ID"])
    dominant_family_S = int(l1_S["DOMINANT_FAMILY_ID"])
    dominant_area_B = int(l1_B["DOMINANT_AREA_ID"])
    dominant_area_S = int(l1_S["DOMINANT_AREA_ID"])

    SHADOW_ENABLED = True
    DOMINANT_FAMILY_CHANGED = dominant_family_S != dominant_family_B
    DOMINANT_AREA_CHANGED = dominant_area_S != dominant_area_B

    DOMINANT_FAMILY_DELTA_HITS = (hits_S[dominant_family_S] if dominant_family_S < len(hits_S) else 0) - (
        hits_B[dominant_family_B] if dominant_family_B < len(hits_B) else 0
    )
    DOMINANCE_RATIO_DELTA = float(l1_S["DOMINANCE_RATIO"]) - float(l1_B["DOMINANCE_RATIO"])
    COVERAGE_RATIO_DELTA = float(l1_S["COVERAGE_RATIO"]) - float(l1_B["COVERAGE_RATIO"])
    UNIQUE_FAMILIES_HIT_DELTA = int(l1_S["UNIQUE_FAMILIES_HIT"]) - int(l1_B["UNIQUE_FAMILIES_HIT"])
    AREA_SPREAD_DELTA = float(l1_S["AREA_SPREAD"]) - float(l1_B["AREA_SPREAD"])
    ENTROPY_DELTA = float(l1_S["NORMALIZED_FAMILY_ENTROPY"]) - float(l1_B["NORMALIZED_FAMILY_ENTROPY"])
    GINI_DELTA = float(l1_S["GINI_COEFFICIENT"]) - float(l1_B["GINI_COEFFICIENT"])
    ALTITUDE_MEAN_DELTA = float(l1_S["MEAN_ALTITUDE_GLOBAL"]) - float(l1_B["MEAN_ALTITUDE_GLOBAL"])
    ALTITUDE_DOMINANT_DELTA = float(l1_S["MEAN_ALTITUDE_DOMINANT"]) - float(l1_B["MEAN_ALTITUDE_DOMINANT"])

    TRAVERSAL_DEPTH_DELTA = int(l2_S["TRAVERSAL_DEPTH_REACHED"]) - int(l2_B["TRAVERSAL_DEPTH_REACHED"])
    REACHABLE_NODES_DELTA = int(l2_S["TOTAL_REACHABLE_NODES"]) - int(l2_B["TOTAL_REACHABLE_NODES"])
    MAX_DISTANCE_DELTA = int(l2_S["MAX_TRAVERSAL_DISTANCE"]) - int(l2_B["MAX_TRAVERSAL_DISTANCE"])
    CROSS_AREA_RATIO_DELTA = float(l2_S["CROSS_AREA_RATIO"]) - float(l2_B["CROSS_AREA_RATIO"])
    LOOP_DENSITY_DELTA = float(l2_S["LOOP_DENSITY"]) - float(l2_B["LOOP_DENSITY"])
    EDGE_UTILIZATION_DELTA = float(l2_S["EDGE_UTILIZATION_RATIO"]) - float(l2_B["EDGE_UTILIZATION_RATIO"])

    visited_B = set(l2_B.get("VISITED_IDS", []))
    visited_S = set(l2_S.get("VISITED_IDS", []))
    inter = visited_B & visited_S
    union = visited_B | visited_S
    union_size = len(union)
    VISITED_JACCARD_SIMILARITY = (len(inter) / union_size) if union_size > 0 else 1.0
    sym_diff_size = len(union) - len(inter)
    VISITED_SYMMETRIC_DIFFERENCE_RATIO = (sym_diff_size / union_size) if union_size > 0 else 0.0

    hit_vector_L1_B = float(l1_B["FAMILY_HIT_VECTOR_L1"])
    hit_vector_L1_S = float(l1_S["FAMILY_HIT_VECTOR_L1"])
    FAMILY_HIT_VECTOR_L1_DELTA = hit_vector_L1_S - hit_vector_L1_B

    dot = 0.0
    norm_b = 0.0
    norm_s = 0.0
    n = min(len(hits_B), len(hits_S), F)
    for f in range(n):
        dot += hits_B[f] * hits_S[f]
        norm_b += hits_B[f] * hits_B[f]
        norm_s += hits_S[f] * hits_S[f]
    denom = math.sqrt(norm_b) * math.sqrt(norm_s) + eps
    HIT_VECTOR_COSINE_SIMILARITY = dot / denom

    top_k_B = _top_k_families(hits_B, F, TOP_K)
    top_k_S = _top_k_families(hits_S, F, TOP_K)
    top_inter = len(top_k_B & top_k_S)
    TOP_K_OVERLAP_RATIO = top_inter / (TOP_K + eps)

    SHADOW_DEVIATION_SCORE = (
        0.35 * (1.0 - HIT_VECTOR_COSINE_SIMILARITY)
        + 0.35 * VISITED_SYMMETRIC_DIFFERENCE_RATIO
        + 0.30 * abs(DOMINANCE_RATIO_DELTA)
    )

    SHADOW_ACCEPTABILITY_GATE = (
        SHADOW_DEVIATION_SCORE <= SHADOW_MAX_DEVIATION
        and abs(CROSS_AREA_RATIO_DELTA) <= SHADOW_MAX_CROSS_AREA_DELTA
        and (not DOMINANT_AREA_CHANGED or SHADOW_ALLOW_AREA_FLIP)
    )

    return {
        "SHADOW_ENABLED": SHADOW_ENABLED,
        "DOMINANT_FAMILY_CHANGED": DOMINANT_FAMILY_CHANGED,
        "DOMINANT_AREA_CHANGED": DOMINANT_AREA_CHANGED,
        "DOMINANT_FAMILY_DELTA_HITS": DOMINANT_FAMILY_DELTA_HITS,
        "DOMINANCE_RATIO_DELTA": DOMINANCE_RATIO_DELTA,
        "COVERAGE_RATIO_DELTA": COVERAGE_RATIO_DELTA,
        "UNIQUE_FAMILIES_HIT_DELTA": UNIQUE_FAMILIES_HIT_DELTA,
        "AREA_SPREAD_DELTA": AREA_SPREAD_DELTA,
        "ENTROPY_DELTA": ENTROPY_DELTA,
        "GINI_DELTA": GINI_DELTA,
        "ALTITUDE_MEAN_DELTA": ALTITUDE_MEAN_DELTA,
        "ALTITUDE_DOMINANT_DELTA": ALTITUDE_DOMINANT_DELTA,
        "TRAVERSAL_DEPTH_DELTA": TRAVERSAL_DEPTH_DELTA,
        "REACHABLE_NODES_DELTA": REACHABLE_NODES_DELTA,
        "MAX_DISTANCE_DELTA": MAX_DISTANCE_DELTA,
        "CROSS_AREA_RATIO_DELTA": CROSS_AREA_RATIO_DELTA,
        "LOOP_DENSITY_DELTA": LOOP_DENSITY_DELTA,
        "EDGE_UTILIZATION_DELTA": EDGE_UTILIZATION_DELTA,
        "VISITED_JACCARD_SIMILARITY": VISITED_JACCARD_SIMILARITY,
        "VISITED_SYMMETRIC_DIFFERENCE_RATIO": VISITED_SYMMETRIC_DIFFERENCE_RATIO,
        "FAMILY_HIT_VECTOR_L1_DELTA": FAMILY_HIT_VECTOR_L1_DELTA,
        "HIT_VECTOR_COSINE_SIMILARITY": HIT_VECTOR_COSINE_SIMILARITY,
        "TOP_K_OVERLAP_RATIO": TOP_K_OVERLAP_RATIO,
        "SHADOW_DEVIATION_SCORE": SHADOW_DEVIATION_SCORE,
        "SHADOW_ACCEPTABILITY_GATE": SHADOW_ACCEPTABILITY_GATE,
    }


def run(input: LayerInput) -> LayerOutput:
    """Layer-3 public entry point. Consumes LayerInput, returns LayerOutput. No other public entry points."""
    t0 = time.perf_counter()
    meta = input.metadata
    layers = meta.get("layers", {})
    l1_B = layers.get(1)
    l2_B = layers.get(2)
    if not l1_B or not l2_B:
        raise ValueError("Layer 3 requires layer 1 and 2 results in input.metadata['layers']")
    hits_B = meta.get("hits", [])
    hits_S = meta.get("hits_shadow", hits_B)
    l1_S = meta.get("l1_shadow", l1_B)
    l2_S = meta.get("l2_shadow", l2_B)
    F = int(meta.get("F", 288))
    A = int(meta.get("A", 12))
    defaults = meta.get("defaults", {})
    result = compute_L3(
        l1_B, l2_B, hits_B,
        l1_S, l2_S, hits_S,
        F=F,
        A=A,
        eps=1e-12,
        **{k: defaults.get(k) for k in ("SHADOW_MAX_DEVIATION", "SHADOW_MAX_CROSS_AREA_DELTA", "SHADOW_ALLOW_AREA_FLIP", "TOP_K") if k in defaults},
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return LayerOutput(
        layer_id=3,
        result=result,
        diagnostics={"layer_id": 3, "execution_time_ms": round(elapsed_ms, 6)},
    )
