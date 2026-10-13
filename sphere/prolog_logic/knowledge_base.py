# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Prolog-style knowledge base: store compiled facts and rules in canonical form.
Deterministic indexing; no inference during storage. Ready for executor consumption.
"""

from __future__ import annotations

from typing import Any


def build_knowledge_base(compiled_items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Build knowledge base from compiled facts and rules.
    Facts indexed by predicate name (list of fact dicts).
    Rules indexed by head predicate name (list of rule dicts).
    rules_ordered: flat list of all rules in source order for deterministic inference.
    Preserves order; duplicate facts do not break execution.
    """
    kb: dict[str, Any] = {"facts": {}, "rules": {}, "rules_ordered": []}
    for item in compiled_items:
        if item.get("type") == "fact":
            add_fact(kb, item)
        elif item.get("type") == "rule":
            add_rule(kb, item)
    return kb


def add_fact(kb: dict[str, Any], fact: dict[str, Any]) -> None:
    """Add a compiled fact to the knowledge base. Indexed by predicate name."""
    if fact.get("type") != "fact":
        raise ValueError("add_fact requires type 'fact'")
    pred = fact.get("predicate", "")
    args = fact.get("args", [])
    if not pred:
        raise ValueError("Fact must have predicate")
    entry = {"predicate": pred, "args": list(args)}
    if pred not in kb["facts"]:
        kb["facts"][pred] = []
    kb["facts"][pred].append(entry)


def add_rule(kb: dict[str, Any], rule: dict[str, Any]) -> None:
    """Add a compiled rule. Must have valid head and non-empty body."""
    if rule.get("type") != "rule":
        raise ValueError("add_rule requires type 'rule'")
    head = rule.get("head")
    body = rule.get("body", [])
    if not head or not isinstance(head, dict):
        raise ValueError("Rule must have valid head")
    pred = head.get("predicate", "")
    if not pred:
        raise ValueError("Rule head must have predicate")
    if not body:
        raise ValueError("Rule must have non-empty body")
    entry = {
        "head": {"predicate": head["predicate"], "args": list(head.get("args", []))},
        "body": [{"predicate": b["predicate"], "args": list(b.get("args", []))} for b in body],
    }
    if pred not in kb["rules"]:
        kb["rules"][pred] = []
    kb["rules"][pred].append(entry)
    kb.setdefault("rules_ordered", []).append(entry)


def query_predicate(kb: dict[str, Any], predicate_name: str) -> list[dict[str, Any]]:
    """Return all stored facts for the given predicate name. Deterministic order."""
    facts = kb.get("facts", {})
    return list(facts.get(predicate_name, []))
