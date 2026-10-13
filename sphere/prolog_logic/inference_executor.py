# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Prolog-style inference executor: deterministic forward-chaining fixed-point over KB.
No recursion, no backtracking, no variable unification in v1.
"""

from __future__ import annotations

from typing import Any

# Iteration guard: no exception on cap; diagnostics["error"] = "iteration_cap_reached", then break.
MAX_INFERENCE_ITERATIONS = 16


def _fact_key(f: dict[str, Any]) -> tuple[str, tuple[Any, ...]]:
    """Hashable key for fact identity."""
    return (f["predicate"], tuple(f.get("args", [])))


def _fact_matches(goal: dict[str, Any], known_keys: set[tuple[str, tuple[Any, ...]]]) -> bool:
    """True if goal exists in known facts (identical predicate and args)."""
    return _fact_key(goal) in known_keys


def evaluate_rule(rule: dict[str, Any], known_facts: set[tuple[str, tuple[Any, ...]]]) -> bool:
    """
    True if all body goals of the rule are satisfied (each exists in known_facts).
    Literal matching only; no variable unification in v1.
    """
    for goal in rule.get("body", []):
        if not _fact_matches(goal, known_facts):
            return False
    return True


def derive_new_facts(
    kb: dict[str, Any],
    known_keys: set[tuple[str, tuple[Any, ...]]],
) -> list[dict[str, Any]]:
    """
    One pass: for each rule in deterministic order, if body satisfied, derive head.
    Returns only facts that were not already in known_keys.
    """
    rules_ordered = kb.get("rules_ordered", [])
    if not rules_ordered:
        # Fallback: collect from kb["rules"] in some order (e.g. sorted by head name)
        for head_pred, rule_list in sorted(kb.get("rules", {}).items()):
            for r in rule_list:
                rules_ordered.append(r)
    new: list[dict[str, Any]] = []
    for rule in rules_ordered:
        if not evaluate_rule(rule, known_keys):
            continue
        head = rule["head"]
        key = _fact_key(head)
        if key not in known_keys:
            new.append({"predicate": head["predicate"], "args": list(head.get("args", []))})
    return new


def infer(kb: dict[str, Any]) -> dict[str, Any]:
    """
    Run deterministic forward-chaining until fixed point.
    Returns artifact: initial_facts, derived_facts, all_facts, inference_steps, iterations.
    Max iterations guarded by MAX_INFERENCE_ITERATIONS.
    """
    # Collect initial facts
    initial_list: list[dict[str, Any]] = []
    for pred, facts in (kb.get("facts") or {}).items():
        for f in facts:
            initial_list.append({"predicate": f["predicate"], "args": list(f.get("args", []))})
    known_keys: set[tuple[str, tuple[Any, ...]]] = set()
    for f in initial_list:
        known_keys.add(_fact_key(f))

    derived_list: list[dict[str, Any]] = []
    inference_steps: list[dict[str, Any]] = []
    rules_ordered = kb.get("rules_ordered", [])
    if not rules_ordered:
        for head_pred, rule_list in sorted((kb.get("rules") or {}).items()):
            for r in rule_list:
                rules_ordered.append(r)

    iteration = 0
    rules_fired = 0
    cap_reached = False
    while iteration < MAX_INFERENCE_ITERATIONS:
        iteration += 1
        added_any = False
        for rule in rules_ordered:
            if not evaluate_rule(rule, known_keys):
                continue
            head = rule["head"]
            key = _fact_key(head)
            if key in known_keys:
                continue
            new_fact = {"predicate": head["predicate"], "args": list(head.get("args", []))}
            derived_list.append(new_fact)
            known_keys.add(key)
            added_any = True
            rules_fired += 1
            body_matched = [
                f"{g['predicate']}({','.join(str(a) for a in g.get('args', []))})"
                for g in rule["body"]
            ]
            body_premises = [g["predicate"] for g in rule["body"]]
            args = head.get("args", [])
            derived_str = head["predicate"] if not args else f"{head['predicate']}({','.join(str(a) for a in args)})"
            inference_steps.append({
                "rule_head": head["predicate"],
                "body_matched": body_matched,
                "body_premises": body_premises,
                "derived": derived_str,
                "iteration": iteration,
            })
        if not added_any:
            break
        if iteration >= MAX_INFERENCE_ITERATIONS:
            cap_reached = True
            break

    all_facts = initial_list + derived_list
    diagnostics: dict[str, Any] = {
        "iterations": iteration,
        "facts_initial": len(initial_list),
        "facts_final": len(all_facts),
        "rules_fired": rules_fired,
    }
    if cap_reached:
        diagnostics["error"] = "iteration_cap_reached"

    return {
        "initial_facts": initial_list,
        "derived_facts": derived_list,
        "all_facts": all_facts,
        "inference_steps": inference_steps,
        "iterations": iteration,
        "diagnostics": diagnostics,
    }
