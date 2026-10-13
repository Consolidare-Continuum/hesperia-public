# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-10 interpretation engine: canonical structured interpretation from L7/L8/L9.
"""

from __future__ import annotations

from typing import Any

from sphere.interpretation.state_classifier import (
    classify_structural_state,
    classify_entropy_state,
    classify_tension_state,
    classify_propagation_state,
)
from sphere.interpretation.event_summarizer import extract_active_events, build_event_summary
from sphere.interpretation.flag_builder import build_interpretation_flags
from sphere.interpretation.diagnostics import build_interpretation_diagnostics


def compute_interpretation_metrics(
    logic_metrics: dict[str, Any],
    shadow_metrics: dict[str, Any],
    propagation_metrics: dict[str, Any],
    dynamism_metrics: dict[str, Any],
    *,
    legacy_logic_outputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Layer-10 canonical entrypoint. Produces deterministic interpretation_metrics
    from logic_metrics, shadow_metrics, propagation_metrics, dynamism_metrics.
    legacy_logic_outputs is optional compatibility only; it does not drive classification.
    """
    shadow_diag = shadow_metrics.get("shadow_diagnostics") or {}
    prop_diag = propagation_metrics.get("propagation_diagnostics") or {}
    logic_diag = logic_metrics.get("logic_diagnostics") or {}

    structural_state, reason = classify_structural_state(logic_metrics, shadow_metrics)
    entropy_state = classify_entropy_state(shadow_diag)
    tension_state = classify_tension_state(shadow_diag)
    propagation_state = classify_propagation_state(prop_diag)

    active_events = extract_active_events(logic_metrics)
    event_summary = build_event_summary(logic_metrics)
    interpretation_flags = build_interpretation_flags(
        structural_state, active_events, logic_metrics, shadow_metrics
    )

    dominant_area_id = logic_diag.get("dominant_area_id")
    corrected = shadow_metrics.get("corrected_area_vector") or []
    dominance_strength = None
    if dominant_area_id is not None and dominant_area_id < len(corrected):
        dominance_strength = float(corrected[dominant_area_id])

    interpretation_diagnostics = build_interpretation_diagnostics(
        dominant_area_id=dominant_area_id,
        dominance_strength=dominance_strength,
        rules_triggered_count=logic_diag.get("rules_triggered_count", 0),
        entropy_after_shadow=float(shadow_diag.get("entropy_after", 0.0)),
        tension_after_shadow=float(shadow_diag.get("tension_after", 0.0)),
        propagation_spread=int(prop_diag.get("active_edges_count") or prop_diag.get("changed_areas_count") or 0),
        structural_state_reason=reason,
        legacy_logic_bridge_used=legacy_logic_outputs is not None and bool(legacy_logic_outputs),
    )

    return {
        "structural_state": structural_state,
        "dominant_area_id": dominant_area_id,
        "dominance_strength": dominance_strength,
        "entropy_state": entropy_state,
        "tension_state": tension_state,
        "propagation_state": propagation_state,
        "active_events": active_events,
        "interpretation_flags": interpretation_flags,
        "event_summary": event_summary,
        "interpretation_diagnostics": interpretation_diagnostics,
    }
