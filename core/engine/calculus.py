"""Main engine calculational features consumed by modules."""

from __future__ import annotations

from typing import Any

from core.result.contract import compute_loopability, compute_stability, compute_tension
from hesperia.engine.tfp_math import (
    compute_confidence_scores,
    detect_interaction_loops,
    detect_tfp_stage,
    estimate_affect_intensity,
)


def concepts_to_family_area_scores(
    concept_hits: list[str], concept_map: dict[str, dict]
) -> tuple[dict[str, float], dict[str, float], list[str], list[str]]:
    family_scores: dict[str, float] = {}
    area_scores: dict[str, float] = {}
    for cid in concept_hits:
        meta = concept_map.get(str(cid)) or {}
        for fid in list(meta.get("family_ids") or []):
            key = str(fid)
            family_scores[key] = family_scores.get(key, 0.0) + 1.0
        for aid in list(meta.get("area_ids") or []):
            key = str(aid)
            area_scores[key] = area_scores.get(key, 0.0) + 1.0
    return (
        dict(sorted(family_scores.items())),
        dict(sorted(area_scores.items())),
        sorted(family_scores),
        sorted(area_scores),
    )


def normalize_area_scores(area_scores: dict[str, float], area_count: int = 12) -> dict[str, float]:
    if not area_scores:
        area_scores = {f"A{i+1}": 0.0 for i in range(area_count)}
    total = sum(float(v) for v in area_scores.values())
    if total <= 0:
        return {k: 1.0 / max(1, len(area_scores)) for k in sorted(area_scores)}
    return {k: float(v) / total for k, v in sorted(area_scores.items())}


def compute_tfp_bundle(
    *,
    family_scores: dict[str, float],
    area_scores: dict[str, float],
    concept_hits: list[str],
    text: str,
    tokens: list[str],
    labels: list[str],
) -> tuple[dict[str, float], dict[str, Any], list[str]]:
    buckets = {label: 0.0 for label in labels}
    for idx, (_fid, val) in enumerate(sorted(family_scores.items())):
        slot = idx % max(1, len(labels))
        buckets[labels[slot]] += float(val)
    total = sum(buckets.values())
    if total > 0:
        buckets = {k: v / total for k, v in buckets.items()}
    activation = {
        "areas": area_scores,
        "families": family_scores,
        "concepts": {str(cid): 1.0 for cid in concept_hits},
    }
    profile = {
        "dominant": max(buckets, key=lambda k: buckets[k]) if buckets else None,
        "confidence": max(buckets.values()) if buckets else 0.0,
        "stage": detect_tfp_stage(area_scores, family_scores),
        "affect_intensity": estimate_affect_intensity(text, tokens),
        "confidence_scores": compute_confidence_scores(activation),
    }
    loops = detect_interaction_loops([{"areas": area_scores, "families": family_scores}] * 2, None)
    conflicts = [k for k, v in buckets.items() if v > 0.4] + ["interaction_loop" for _ in loops]
    return buckets, profile, conflicts


def compute_metrics_bundle(
    *, area_scores: dict[str, float], family_scores: dict[str, float], area_count: int = 12, family_count: int = 24
) -> dict[str, Any]:
    area_vector = [float(area_scores.get(f"A{i+1}", 0.0)) for i in range(area_count)]
    fam_total = sum(float(v) for v in family_scores.values())
    if fam_total <= 0:
        family_vector = [1.0 / family_count for _ in range(family_count)]
    else:
        family_vector = [float(family_scores.get(f"F{i+1}", 0.0)) / fam_total for i in range(family_count)]
    return {
        "dominant_area": int(max(range(len(area_vector)), key=lambda i: area_vector[i])) if area_vector else 0,
        "dominant_family": int(max(range(len(family_vector)), key=lambda i: family_vector[i])) if family_vector else 0,
        "tension": compute_tension(area_vector),
        "loopability": compute_loopability(
            {"segment_count": 1, "transition_count": 0, "stability_window": 1.0, "jump_distance": 0.0}
        ),
        "stability": compute_stability([0.0]),
        "area_vector": area_vector,
        "family_vector": family_vector,
    }

