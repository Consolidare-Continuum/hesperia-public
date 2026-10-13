"""Aggregate hex state into family and area vectors."""

from __future__ import annotations

from typing import Any


def aggregate_hex_state(
    concept_weights: dict[str, float],
    concept_index: dict[str, dict]
) -> tuple[dict[str, float], dict[str, float]]:
    family: dict[str, float] = {}
    area: dict[str, float] = {}
    for concept_id, weight in concept_weights.items():
        meta = concept_index.get(concept_id, {})
        for family_id in meta.get("family_ids", []):
            family[family_id] = family.get(family_id, 0.0) + float(weight)
        for area_id in meta.get("area_ids", []):
            area[area_id] = area.get(area_id, 0.0) + float(weight)
    return family, area


def cross_family_relation_sketch(
    family_activation: dict[str, float],
    *,
    top_k: int = 6,
) -> dict[str, Any]:
    """
    Deterministic top-family pairs by product of masses (Ethan PO-25 sketch).

    Returns JSON-serializable summary for instrumentation / reports.
    """
    items = sorted(family_activation.items(), key=lambda x: float(x[1]), reverse=True)
    top = [fid for fid, w in items[: max(1, top_k)] if float(w) > 0]
    pairs: list[dict[str, Any]] = []
    for i, a in enumerate(top):
        for b in top[i + 1 :]:
            wa = float(family_activation.get(a, 0.0))
            wb = float(family_activation.get(b, 0.0))
            pairs.append(
                {
                    "family_a": a,
                    "family_b": b,
                    "coupling_score": round(wa * wb, 8),
                }
            )
    pairs.sort(key=lambda x: (-float(x["coupling_score"]), x["family_a"], x["family_b"]))
    return {"top_families": top, "family_pairs_by_mass_product": pairs[:top_k]}

