# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-9 Rule engine: evaluate rules against structural facts, return triggered rules and diagnostics.
Strictly downstream of measurement layers; strictly upstream of interpretation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import diagnostics, rule_runtime, trigger_registry
from .rule_evaluator import evaluate_structural_rules
from .rule_registry import STRUCTURAL_RULES

_DEFAULT_SPEC = Path(__file__).resolve().parents[2] / "spec" / "logic_rules.yaml"


def compute_logic_metrics(
    shadow_metrics: dict[str, Any],
    propagation_metrics: dict[str, Any],
    dynamism_metrics: dict[str, Any],
    *,
    previous_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Layer-9 structural logic entrypoint. Consumes Layer-8 (shadow) and Layer-7 (propagation) signals.
    Returns logic_metrics: triggered_rules, dominance_events, entropy_events, tension_events,
    anomaly_flags, logic_diagnostics. Uses core/math only for dominance; no math implementation here.
    """
    corrected_area = shadow_metrics.get("corrected_area_vector") or []
    shadow_diag = shadow_metrics.get("shadow_diagnostics") or {}
    prop_diag = propagation_metrics.get("propagation_diagnostics") or {}

    from core.math.vector_ops import detect_dominant_area
    import numpy as np
    av = np.asarray(corrected_area, dtype=np.float64) if corrected_area else np.zeros(12)
    if av.size != 12:
        av = np.resize(av, 12) if av.size < 12 else av[:12]
    dominant_area_id = int(detect_dominant_area(av, num_areas=12))

    state: dict[str, Any] = {
        "corrected_area_vector": list(av),
        "corrected_family_counts": shadow_metrics.get("corrected_family_counts") or [],
        "area_vector": list(av),
        "shadow_diagnostics": shadow_diag,
        "propagation_diagnostics": prop_diag,
        "dominant_area_id": dominant_area_id,
        "stability_index": dynamism_metrics.get("stability_index"),
        "jump_rate": dynamism_metrics.get("jump_rate"),
        "curvature": dynamism_metrics.get("curvature"),
    }

    events = evaluate_structural_rules(state, previous_state)
    triggered = events["triggered_rules"]
    rules_evaluated = len(STRUCTURAL_RULES)
    rules_triggered = len(triggered)
    entropy_after = float(shadow_diag.get("entropy_after", 0.0))
    tension_after = float(shadow_diag.get("tension_after", 0.0))
    propagation_spread = int(prop_diag.get("active_edges_count") or prop_diag.get("changed_areas_count") or 0)

    logic_diagnostics = diagnostics.build_logic_diagnostics(
        rules_evaluated_count=rules_evaluated,
        rules_triggered_count=rules_triggered,
        dominant_area=dominant_area_id,
        entropy_after_shadow=entropy_after,
        tension_after_shadow=tension_after,
        propagation_spread=propagation_spread,
    )

    return {
        "triggered_rules": events["triggered_rules"],
        "dominance_events": events["dominance_events"],
        "entropy_events": events["entropy_events"],
        "tension_events": events["tension_events"],
        "anomaly_flags": events["anomaly_flags"],
        "logic_diagnostics": logic_diagnostics,
    }


def _collect_matched_facts(rule: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    """Extract fact names and values from rule conditions that are present in facts."""
    out: dict[str, Any] = {}
    conds = rule.get("conditions") or {}
    for key in ("all", "any"):
        if key not in conds:
            continue
        for c in conds[key]:
            name = c.get("fact")
            if name is not None and name in facts:
                out[name] = facts[name]
    return out


def _ordered_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enabled rules only, sorted by priority descending, tie-break rule_id ascending."""
    enabled = [r for r in rules if r.get("enabled") is True]
    return sorted(enabled, key=lambda r: (-int(r.get("priority", 0)), r.get("rule_id", "")))


def evaluate_rules(
    facts: dict[str, Any],
    rules: list[dict[str, Any]] | None = None,
    rule_spec_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Layer-9 entrypoint: evaluate rules against facts, return deterministic diagnostics artifact.

    Rules: either pass `rules` list (already loaded/validated) or set `rule_spec_path`.
    If both omitted, uses spec/logic_rules.yaml. Validates rules once if loaded from path.

    Returns:
      triggered_rules: list of triggered rule objects with matched_facts
      structural_diagnostics: list of diagnostic dicts (traceable, machine-clean)
      rule_trigger_registry: counts and ordering by severity/code
    """
    if rules is None:
        path = rule_spec_path if rule_spec_path is not None else _DEFAULT_SPEC
        rules = rule_runtime.load_rules(path)
        rule_runtime.validate_rule_spec(rules)
    else:
        rule_runtime.validate_rule_spec(rules)

    ordered = _ordered_rules(rules)
    triggered: list[dict[str, Any]] = []
    for r in ordered:
        if not rule_runtime.evaluate_condition_group(r.get("conditions") or {}, facts):
            continue
        matched = _collect_matched_facts(r, facts)
        triggered.append({
            "rule_id": r.get("rule_id", ""),
            "name": r.get("name", ""),
            "priority": r.get("priority", 0),
            "severity": r.get("severity", "medium"),
            "diagnostic_code": r.get("diagnostic_code", ""),
            "diagnostic_message": r.get("diagnostic_message", ""),
            "matched_facts": matched,
        })

    structural_diagnostics = diagnostics.build_structural_diagnostics(triggered, facts)
    rule_trigger_registry = trigger_registry.build_rule_trigger_registry(triggered, facts)

    return {
        "triggered_rules": triggered,
        "structural_diagnostics": structural_diagnostics,
        "rule_trigger_registry": rule_trigger_registry,
    }


