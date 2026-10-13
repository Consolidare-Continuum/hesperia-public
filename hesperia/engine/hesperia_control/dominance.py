# Strict dominance (HC-05) — segment-level readout policy. Copyright © 2026 igareosh.com.
from __future__ import annotations

from typing import Literal, Mapping

Outcome = Literal["dominant", "weak_dominant", "mixed", "invalid"]


def classify_segment_dominance(
    area_scores: Mapping[str, float],
    *,
    dominance_min: float = 0.5,
    dominance_gap_min: float = 0.12,
    top2_max_sum_for_clear: float = 0.78,
) -> tuple[Outcome, str | None, tuple[str, str] | None]:
    """
    Classify segment using top-two areas. Returns (outcome, top_area_id or None, (first, second) ids).
    Does not mutate inputs. Deterministic tie-break: lexicographic area id.
    """
    if not area_scores:
        return "invalid", None, None
    sorted_items = sorted(area_scores.items(), key=lambda kv: (-kv[1], kv[0]))
    top_id, top_s = sorted_items[0]
    second_s = sorted_items[1][1] if len(sorted_items) > 1 else 0.0
    gap = top_s - second_s
    total = sum(max(0.0, float(v)) for v in area_scores.values()) or 1.0
    norm_top = top_s / total
    if norm_top < dominance_min or gap < dominance_gap_min:
        return "mixed", top_id, (sorted_items[0][0], sorted_items[1][0]) if len(sorted_items) > 1 else None
    top2_sum = top_s + second_s
    if top2_sum <= total * top2_max_sum_for_clear and gap >= dominance_gap_min:
        return "dominant", top_id, (sorted_items[0][0], sorted_items[1][0])
    return "weak_dominant", top_id, (sorted_items[0][0], sorted_items[1][0])
