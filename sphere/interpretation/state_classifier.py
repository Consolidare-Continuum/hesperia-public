# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-10 state classification: structural_state, entropy_state, tension_state, propagation_state.
Rule-based and deterministic; no math implementation — uses logic events and diagnostics only.
"""

from __future__ import annotations

from typing import Any

# Thresholds for classification (deterministic)
DOMINANT_SHARE_HIGH = 0.35
ENTROPY_DROP_SIGNIFICANT = 0.15
TENSION_DELTA_ELEVATED = 0.10
SPREAD_MINIMAL = 0
SPREAD_MODERATE = 2
SPREAD_WIDE = 10


def classify_structural_state(
    logic_metrics: dict[str, Any],
    shadow_metrics: dict[str, Any],
) -> tuple[str, str]:
    """
    Classify overall structural state from corrected vectors and logic events.
    Returns (structural_state, reason).
    """
    triggered = [e.get("type") for e in logic_metrics.get("triggered_rules", []) if isinstance(e, dict)]
    logic_diag = logic_metrics.get("logic_diagnostics") or {}
    shadow_diag = shadow_metrics.get("shadow_diagnostics") or {}
    dominant_area_id = logic_diag.get("dominant_area_id", 0)
    corrected = shadow_metrics.get("corrected_area_vector") or []
    share = float(corrected[dominant_area_id]) if dominant_area_id < len(corrected) else 0.0
    entropy_after = float(shadow_diag.get("entropy_after", 0.0))

    if "dominance_transition" in triggered:
        return "unstable_transition", "dominance_transition_triggered"
    if "tension_increase" in triggered:
        tension_delta = 0.0
        for e in logic_metrics.get("tension_events", []):
            if isinstance(e, dict) and "delta_tension" in e:
                tension_delta = max(tension_delta, float(e["delta_tension"]))
        if tension_delta >= TENSION_DELTA_ELEVATED:
            return "tension_elevated", "tension_increase_triggered"
    if "propagation_spread" in triggered and share < DOMINANT_SHARE_HIGH:
        return "diffuse_spread", "propagation_spread_weak_dominance"
    if share >= DOMINANT_SHARE_HIGH and entropy_after < 2.5:
        return "focused_dominant", "high_share_low_entropy"
    if share < DOMINANT_SHARE_HIGH and entropy_after >= 2.0:
        return "distributed_balanced", "no_strong_dominance_high_entropy"
    if share >= DOMINANT_SHARE_HIGH:
        return "focused_dominant", "high_share"
    return "distributed_balanced", "default"


def classify_entropy_state(shadow_diagnostics: dict[str, Any]) -> str:
    """Derive entropy state label from shadow_diagnostics."""
    before = float(shadow_diagnostics.get("entropy_before", 0.0))
    after = float(shadow_diagnostics.get("entropy_after", 0.0))
    delta = before - after
    if delta >= ENTROPY_DROP_SIGNIFICANT:
        return "reduced_after_shadow"
    if abs(delta) < 0.05:
        return "stable"
    return "elevated"


def classify_tension_state(shadow_diagnostics: dict[str, Any]) -> str:
    """Derive tension state from post-shadow tension and delta."""
    after = float(shadow_diagnostics.get("tension_after", 0.0))
    before = float(shadow_diagnostics.get("tension_before", 0.0))
    delta = after - before
    if delta >= TENSION_DELTA_ELEVATED:
        return "elevated"
    if delta <= -0.05:
        return "reduced"
    return "normal"


def classify_propagation_state(propagation_diagnostics: dict[str, Any]) -> str:
    """Derive propagation state from propagation_diagnostics."""
    spread = int(propagation_diagnostics.get("active_edges_count") or propagation_diagnostics.get("changed_areas_count") or 0)
    if spread <= SPREAD_MINIMAL:
        return "minimal_spread"
    if spread < SPREAD_WIDE:
        return "moderate_spread"
    return "wide_spread"
