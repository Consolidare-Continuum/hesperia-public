# HESPERIA — TFP Stage Detection
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Compute TFP therapy phase from areas: chaotic, defense_clarification, interpretation, integration.
Uses A3 defenses, A2 object relations, A4 aggression, A7 love capacity.
"""

from __future__ import annotations

from typing import Any

TFP_STAGES = (
    "chaotic",
    "defense_clarification",
    "interpretation",
    "integration",
)


def detect_tfp_stage(
    areas: dict[str, float],
    families: dict[str, float] | None = None,
) -> str:
    """
    Map current activation (areas, optionally families) to one TFP phase.

    Heuristics:
    - High A4 + high A3, low A7 → chaotic
    - High A3, moderate A4 → defense_clarification
    - Moderate A2, A3, A4 → interpretation
    - Higher A7, lower A4, A2 integrated → integration
    """
    areas = areas or {}
    a2 = areas.get("A2", 0.0)
    a3 = areas.get("A3", 0.0)
    a4 = areas.get("A4", 0.0)
    a7 = areas.get("A7", 0.0)

    if a4 >= 0.5 and a3 >= 0.4 and a7 < 0.3:
        return "chaotic"
    if a3 >= 0.45 and a4 >= 0.2:
        return "defense_clarification"
    if a7 >= 0.5 and a4 < 0.4:
        return "integration"
    if a2 >= 0.2 or a3 >= 0.2:
        return "interpretation"
    return "chaotic"


def stage_from_timeline(
    timeline: list[dict[str, Any]],
    last_n: int = 1,
) -> str:
    """
    Compute TFP stage from the last_n windows of an activation timeline.
    """
    if not timeline or last_n < 1:
        return "chaotic"
    slice_ = timeline[-last_n:]
    areas_agg: dict[str, float] = {}
    for step in slice_:
        for k, v in (step.get("areas") or {}).items():
            areas_agg[k] = areas_agg.get(k, 0.0) + v
    n = len(slice_)
    if n > 0:
        areas_agg = {k: v / n for k, v in areas_agg.items()}
    return detect_tfp_stage(areas_agg)
