# HESPERIA — LEVEL 13 Activation propagation over family embedding
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Controlled propagation of activation using family_embedding_tfp.yaml:
within family (concept → family), within area (zone neighbors), across areas via bridges.
Turns embedding into dynamic topology for KME.
"""

from __future__ import annotations

from typing import Any

from sphere.topology.family_embedding import (
    ZONE_KEYS,
    get_area_zones,
    get_bridges,
    get_composite_family_id,
)
from sphere.topology.propagation_weights_loader import (
    get_bridge_weight,
    get_within_area_spread,
    load_propagation_weights,
)


def normalize_scores(scores: dict[str, float], max_val: float = 1.0) -> dict[str, float]:
    """Ограничить значения: каждый score не больше max_val (по умолчанию 1.0)."""
    if max_val <= 0:
        return scores
    return {k: min(max_val, max(0.0, v)) for k, v in scores.items()}


def propagate_within_area(
    area_id: str,
    family_scores: dict[str, float],
    embedding: dict[str, Any],
    weights: dict[str, Any] | None = None,
) -> dict[str, float]:
    """
    Распространение внутри области по зонам: center → inner_ring, inner ↔ middle, middle ↔ outer.
    Веса из spec/propagation_weights.yaml (weights или load_propagation_weights()).
    """
    zones = get_area_zones(embedding, area_id)
    out = dict(family_scores)
    spread = get_within_area_spread(weights)
    for source_zone, target_zone, coef in spread:
        src_families = zones.get(source_zone) or []
        tgt_families = zones.get(target_zone) or []
        for local_s in src_families:
            fid_s = get_composite_family_id(area_id, local_s)
            score_s = family_scores.get(fid_s, 0.0)
            if score_s <= 0:
                continue
            add = score_s * coef
            for local_t in tgt_families:
                fid_t = get_composite_family_id(area_id, local_t)
                out[fid_t] = out.get(fid_t, 0.0) + add
    return out


def propagate_across_bridges(
    family_scores: dict[str, float],
    embedding: dict[str, Any],
    weights: dict[str, Any] | None = None,
) -> dict[str, float]:
    """
    Если активна мостовая семья, передать активацию на другой конец моста.
    Вес из spec/propagation_weights.yaml (bridge_weight).
    """
    bridges = get_bridges(embedding)
    out = dict(family_scores)
    bridge_w = get_bridge_weight(weights)
    for b in bridges:
        fr = b.get("from")
        to = b.get("to")
        if not fr or not to:
            continue
        score_fr = family_scores.get(fr, 0.0)
        if score_fr <= 0:
            continue
        out[to] = out.get(to, 0.0) + score_fr * bridge_w
    return out


def recompute_area_scores(family_scores: dict[str, float]) -> dict[str, float]:
    """Пересчитать области из семей: area = сумма family_scores по семьям этой области."""
    area_scores: dict[str, float] = {}
    for fkey, score in family_scores.items():
        if "_" in fkey:
            area = fkey.split("_")[0]
        else:
            continue
        area_scores[area] = area_scores.get(area, 0.0) + score
    return area_scores


def propagate_activation(
    activation: dict[str, Any],
    embedding: dict[str, Any],
    normalize_after: bool = True,
    propagation_trace: bool = True,
    weights: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Полный пайплайн распространения: внутри области (по зонам) → по мостам → пересчёт областей.
    Веса из spec/propagation_weights.yaml при weights=None (LEVEL 15 calibration).
    """
    families = dict(activation.get("families") or {})
    trace: list[str] = []
    if weights is None:
        weights = load_propagation_weights()

    # Areas that have embedding (pilot A2, A3, A4, A10)
    area_ids = [k for k in embedding if k.startswith("A") and k[1:].isdigit() and isinstance(embedding.get(k), dict)]
    if not area_ids:
        area_ids = ["A2", "A3", "A4", "A10"]

    # Rule 2 — Intra-area spread
    for aid in area_ids:
        before = sum(families.get(get_composite_family_id(aid, f), 0) for z in ZONE_KEYS for f in (get_area_zones(embedding, aid).get(z) or []))
        families = propagate_within_area(aid, families, embedding, weights=weights)
        after = sum(families.get(get_composite_family_id(aid, f), 0) for z in ZONE_KEYS for f in (get_area_zones(embedding, aid).get(z) or []))
        if propagation_trace and after > before:
            trace.append(f"within_area:{aid}")

    # Rule 3 — Bridge spread
    families = propagate_across_bridges(families, embedding, weights=weights)
    if propagation_trace and get_bridges(embedding):
        trace.append("across_bridges")

    if normalize_after:
        families = normalize_scores(families, max_val=1.0)

    areas = recompute_area_scores(families)
    if normalize_after and areas:
        m = max(areas.values())
        if m > 0:
            areas = {k: min(1.0, v / m) for k, v in areas.items()}

    result: dict[str, Any] = {
        "families": families,
        "areas": areas,
    }
    if propagation_trace:
        result["propagation_trace"] = trace
    return result
