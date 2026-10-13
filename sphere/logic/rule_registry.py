# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-9 structural rule registry. Rules are deterministic predicates;
they call core/math when needed and return event dict or None.
"""

from __future__ import annotations

from typing import Any

from .rule_types import (
    DOMINANT_AREA_SHARE_THRESHOLD,
    ENTROPY_DROP_THRESHOLD,
    TENSION_INCREASE_THRESHOLD,
    PROPAGATION_SPREAD_AREAS_THRESHOLD,
    EVENT_DOMINANT_AREA,
    EVENT_ENTROPY_DROP,
    EVENT_TENSION_INCREASE,
    EVENT_PROPAGATION_SPREAD,
    EVENT_DOMINANCE_TRANSITION,
)


def dominant_area_rule(state: dict[str, Any], _previous: dict[str, Any] | None) -> dict[str, Any] | None:
    """Trigger when a single area dominates: dominant_area_share >= threshold."""
    area_vector = state.get("corrected_area_vector") or state.get("area_vector")
    if not area_vector or len(area_vector) < 1:
        return None
    area_id = state.get("dominant_area_id")
    if area_id is None:
        from core.math.vector_ops import detect_dominant_area
        area_id = detect_dominant_area(area_vector, num_areas=len(area_vector))
    share = float(area_vector[area_id]) if area_id < len(area_vector) else 0.0
    if share >= DOMINANT_AREA_SHARE_THRESHOLD:
        return {"type": EVENT_DOMINANT_AREA, "area_id": int(area_id), "share": share}
    return None


def entropy_drop_rule(state: dict[str, Any], _previous: dict[str, Any] | None) -> dict[str, Any] | None:
    """Trigger when entropy dropped significantly (shadow focusing)."""
    diag = state.get("shadow_diagnostics") or {}
    before = diag.get("entropy_before")
    after = diag.get("entropy_after")
    if before is None or after is None:
        return None
    delta = float(before) - float(after)
    if delta >= ENTROPY_DROP_THRESHOLD:
        return {"type": EVENT_ENTROPY_DROP, "delta_entropy": delta}
    return None


def tension_increase_rule(state: dict[str, Any], _previous: dict[str, Any] | None) -> dict[str, Any] | None:
    """Trigger when structural tension increased after shadow."""
    diag = state.get("shadow_diagnostics") or {}
    before = diag.get("tension_before")
    after = diag.get("tension_after")
    if before is None or after is None:
        return None
    delta = float(after) - float(before)
    if delta >= TENSION_INCREASE_THRESHOLD:
        return {"type": EVENT_TENSION_INCREASE, "delta_tension": delta}
    return None


def propagation_spread_rule(state: dict[str, Any], _previous: dict[str, Any] | None) -> dict[str, Any] | None:
    """Trigger when propagation affected many areas."""
    prop_diag = state.get("propagation_diagnostics") or {}
    areas_affected = prop_diag.get("active_edges_count") or prop_diag.get("changed_areas_count") or 0
    try:
        areas_affected = int(areas_affected)
    except (TypeError, ValueError):
        return None
    if areas_affected >= PROPAGATION_SPREAD_AREAS_THRESHOLD:
        return {"type": EVENT_PROPAGATION_SPREAD, "areas_affected": areas_affected}
    return None


def dominance_transition_rule(state: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any] | None:
    """Trigger when dominant area changed from previous state."""
    if not previous:
        return None
    prev_dom = previous.get("dominant_area_id")
    curr_dom = state.get("dominant_area_id")
    if prev_dom is None or curr_dom is None:
        return None
    if int(prev_dom) != int(curr_dom):
        return {
            "type": EVENT_DOMINANCE_TRANSITION,
            "from": int(prev_dom),
            "to": int(curr_dom),
        }
    return None


# Ordered list of structural rules (evaluated in sequence)
STRUCTURAL_RULES = [
    dominant_area_rule,
    entropy_drop_rule,
    tension_increase_rule,
    propagation_spread_rule,
    dominance_transition_rule,
]
