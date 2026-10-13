# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Prolog inference engine: optional L9b layer.
Consumes logic_metrics, interpretation_metrics, shadow_metrics; runs forward-chaining;
returns derived_facts, rule_traces (frozen schema), prolog_diagnostics. Does not replace deterministic L9.
"""

from __future__ import annotations

from typing import Any

from sphere.prolog_logic.rule_compiler import compile_knowledge_base
from sphere.prolog_logic.knowledge_base import build_knowledge_base
from sphere.prolog_logic.inference_executor import infer

# Frozen input fact schema (legacy/docs/refactor_notes/prolog_fact_schema.md)
# Emission rule: emitted_fact ∈ ALLOWED_INPUT_FACTS ∪ OPTIONAL_DIAGNOSTIC_FACTS. Everything else ignored.
ALLOWED_INPUT_FACTS = frozenset({
    "dominant_area",
    "entropy_drop",
    "tension_increase",
    "dominance_transition",
    "propagation_spread",
})
OPTIONAL_DIAGNOSTIC_FACTS = frozenset({
    "low_entropy",
    "high_entropy",
    "stable_structure",
})
ALLOWED_FACTS = ALLOWED_INPUT_FACTS | OPTIONAL_DIAGNOSTIC_FACTS

# Deterministic rule order: (rule_name, rule_line) sorted by rule name before execution.
# Same input → same inference order. With extra_rules: rules = sorted(DEFAULT_RULES + extra_rules, key=name).
DEFAULT_RULES = [
    ("elevated_risk_rule", "elevated_risk :- tension_increase, dominance_transition."),
    ("propagation_wave_rule", "propagation_wave :- propagation_spread."),
    ("structural_focus_rule", "structural_focus :- dominant_area, entropy_drop."),
    ("transition_risk_rule", "transition_risk :- dominance_transition."),
]
DEFAULT_RULES = sorted(DEFAULT_RULES, key=lambda r: r[0])

# Frozen rule trace schema: exactly these keys per entry.
TRACE_KEYS = frozenset({"rule", "premises", "derived", "iteration"})


def _metrics_to_fact_lines(
    logic_metrics: dict[str, Any],
    interpretation_metrics: dict[str, Any],
    shadow_metrics: dict[str, Any] | None,
) -> list[str]:
    """Convert layer outputs to Prolog fact lines. Only allowed/optional facts (frozen schema)."""
    seen: set[str] = set()
    lines: list[str] = []
    for event in interpretation_metrics.get("active_events") or []:
        if event and isinstance(event, str):
            atom = event.strip().lower().replace("-", "_")
            if atom and atom in ALLOWED_FACTS and atom not in seen:
                seen.add(atom)
                lines.append(f"{atom}.")
    for rule in logic_metrics.get("triggered_rules") or []:
        if isinstance(rule, dict):
            t = rule.get("type")
            if t and isinstance(t, str):
                atom = t.strip().lower().replace("-", "_")
                if atom and atom in ALLOWED_FACTS and atom not in seen:
                    seen.add(atom)
                    lines.append(f"{atom}.")
    return sorted(lines)  # lexicographic order before inference


def _trace_entry(step: dict[str, Any]) -> dict[str, Any]:
    """Map inference step to frozen trace schema. set(trace.keys()) == TRACE_KEYS."""
    rule_head = step.get("rule_head", "")
    premises = list(step.get("body_premises", []))
    if not premises and step.get("body_matched"):
        premises = [s.split("(")[0] for s in step.get("body_matched", [])]
    derived = rule_head
    out: dict[str, Any] = {
        "rule": f"{rule_head}_rule",
        "premises": premises,
        "derived": derived,
        "iteration": int(step.get("iteration", 0)),
    }
    assert set(out.keys()) == TRACE_KEYS
    return out


def _run_inference_safe(kb: dict[str, Any]) -> dict[str, Any]:
    """Run infer(); executor returns diagnostics and does not raise on iteration cap."""
    try:
        return infer(kb)
    except RuntimeError as e:
        return {
            "initial_facts": [],
            "derived_facts": [],
            "all_facts": [],
            "inference_steps": [],
            "iterations": 0,
            "diagnostics": {
                "iterations": 0,
                "facts_initial": 0,
                "facts_final": 0,
                "rules_fired": 0,
                "error": str(e),
            },
        }


def compute_prolog_inference(
    logic_metrics: dict[str, Any],
    interpretation_metrics: dict[str, Any],
    shadow_metrics: dict[str, Any] | None = None,
    *,
    extra_rules: list[str] | None = None,
    extra_facts: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run optional Prolog-style forward-chaining over structural metrics.

    Inputs:
      logic_metrics: Layer-9 output (triggered_rules, etc.)
      interpretation_metrics: Layer-10 output (active_events, etc.)
      shadow_metrics: optional Layer-8 (unused in v1 beyond optional diagnostics)

    Outputs:
      derived_facts: list of {predicate, args} derived by rules
      rule_traces: list of {rule, premises, derived, iteration} (frozen schema, no free text)
      prolog_diagnostics: iterations, facts_initial, facts_final, rules_fired, error if any
    """
    # Facts normalized: sorted(set(base) | set(extra)) for deterministic order
    fact_lines = _metrics_to_fact_lines(logic_metrics, interpretation_metrics, shadow_metrics or {})
    facts = sorted(set(fact_lines) | set(extra_facts or []))
    # Rules: DEFAULT_RULES already sorted by name; if extra_rules (string lines), sort combined list
    rule_lines_ordered = [line for _, line in DEFAULT_RULES]
    if extra_rules:
        rule_lines_ordered = sorted(rule_lines_ordered + list(extra_rules))
    all_lines = list(facts) + list(rule_lines_ordered)
    try:
        compiled = compile_knowledge_base(all_lines)
    except ValueError as e:
        return {
            "derived_facts": [],
            "rule_traces": [],
            "prolog_diagnostics": {
                "compile_error": str(e),
                "iterations": 0,
                "facts_initial": 0,
                "facts_final": 0,
                "rules_fired": 0,
            },
        }
    kb = build_knowledge_base(compiled)
    raw = _run_inference_safe(kb)
    derived = raw.get("derived_facts", [])
    steps = raw.get("inference_steps", [])
    rule_traces = [_trace_entry(s) for s in steps]
    diag = dict(raw.get("diagnostics", {}))
    if not diag:
        diag = {
            "iterations": raw.get("iterations", 0),
            "facts_initial": len(raw.get("initial_facts", [])),
            "facts_final": len(raw.get("all_facts", [])),
            "rules_fired": sum(1 for _ in steps),
        }
    if raw.get("_inference_error"):
        diag["error"] = raw["_inference_error"]
    return {
        "derived_facts": derived,
        "rule_traces": rule_traces,
        "prolog_diagnostics": diag,
    }
