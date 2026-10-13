# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Prolog explanation layer: explain inference chains.
Output: { fact, derived_from, rules_applied }.
"""

from __future__ import annotations

from typing import Any


def build_inference_tree(inference_steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Build a tree-friendly list of inference steps (rule, premises, derived).
    Each node: { "fact", "derived_from": [...], "rule" }.
    """
    tree: list[dict[str, Any]] = []
    for step in inference_steps or []:
        derived = step.get("derived", step.get("rule_head", ""))
        premises = step.get("premises", step.get("body_premises", []))
        rule = step.get("rule", "")
        tree.append({
            "fact": derived,
            "derived_from": list(premises) if premises else [],
            "rule": rule,
        })
    return tree


def trace_rule_chain(prolog_output: dict[str, Any], fact: str) -> list[dict[str, Any]]:
    """
    Trace back which rules and premises led to a given fact.
    Returns list of steps that derive or use this fact.
    """
    steps = prolog_output.get("inference_steps") or prolog_output.get("rule_traces") or []
    chain = []
    for step in steps:
        derived = step.get("derived", step.get("rule_head", ""))
        if derived == fact or fact in (step.get("premises") or step.get("body_premises") or []):
            chain.append({
                "rule": step.get("rule", ""),
                "premises": step.get("premises", step.get("body_premises", [])),
                "derived": derived,
            })
    return chain


def generate_explanation(prolog_output: dict[str, Any], fact: str | None = None) -> dict[str, Any]:
    """
    Generate explanation for a derived fact (or full inference).
    Output: { fact, derived_from, rules_applied }.
    If fact is None, summarizes all derived facts with their explanations.
    """
    steps = prolog_output.get("inference_steps") or prolog_output.get("rule_traces") or []
    rules_applied = [s.get("rule", "") for s in steps if s.get("rule")]
    if fact is not None:
        chain = trace_rule_chain(prolog_output, fact)
        derived_from = []
        for c in chain:
            derived_from.extend(c.get("premises", []))
        return {
            "fact": fact,
            "derived_from": list(dict.fromkeys(derived_from)),
            "rules_applied": [c.get("rule", "") for c in chain],
        }
    # Full summary: each derived fact with its explanation
    tree = build_inference_tree(steps)
    return {
        "fact": None,
        "derived_from": [],
        "rules_applied": rules_applied,
        "inference_tree": tree,
    }


__all__ = [
    "build_inference_tree",
    "trace_rule_chain",
    "generate_explanation",
]
