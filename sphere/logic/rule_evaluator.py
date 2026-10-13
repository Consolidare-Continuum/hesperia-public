# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-9 rule evaluator: iterate over structural rules, collect events by type.
Purely behavioral; rules call core/math where needed.
"""

from __future__ import annotations

from typing import Any

from .rule_registry import STRUCTURAL_RULES
from .rule_types import (
    EVENT_DOMINANT_AREA,
    EVENT_ENTROPY_DROP,
    EVENT_TENSION_INCREASE,
    EVENT_PROPAGATION_SPREAD,
    EVENT_DOMINANCE_TRANSITION,
)


def evaluate_structural_rules(
    state: dict[str, Any],
    previous_state: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Evaluate all structural rules. Returns events grouped by type.
    state: current Layer-8/7 signals (corrected_area_vector, shadow_diagnostics, etc.)
    previous_state: optional, for dominance transition.
    """
    dominance_events: list[dict[str, Any]] = []
    entropy_events: list[dict[str, Any]] = []
    tension_events: list[dict[str, Any]] = []
    anomaly_flags: list[str] = []
    triggered: list[dict[str, Any]] = []

    for rule_fn in STRUCTURAL_RULES:
        result = rule_fn(state, previous_state)
        if result is None:
            continue
        triggered.append(result)
        t = result.get("type", "")
        if t == EVENT_DOMINANT_AREA or t == EVENT_DOMINANCE_TRANSITION:
            dominance_events.append(result)
        elif t == EVENT_ENTROPY_DROP:
            entropy_events.append(result)
        elif t == EVENT_TENSION_INCREASE:
            tension_events.append(result)
        elif t == EVENT_PROPAGATION_SPREAD:
            anomaly_flags.append("propagation_spread")

    return {
        "triggered_rules": triggered,
        "dominance_events": dominance_events,
        "entropy_events": entropy_events,
        "tension_events": tension_events,
        "anomaly_flags": anomaly_flags,
    }
