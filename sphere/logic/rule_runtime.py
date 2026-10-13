# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-9 Rule runtime: load rules, validate spec, evaluate condition trees.
Purely boolean evaluation; no fuzzy logic, no scoring, no learned behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ALLOWED_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
SUPPORTED_OPS = frozenset({"eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in"})
CONDITION_GROUPS = frozenset({"all", "any"})


def load_rules(rule_spec_path: str | Path) -> list[dict[str, Any]]:
    """
    Load and return rule list from YAML spec.
    Expects top-level 'rules' key. Does not validate; call validate_rule_spec after.
    """
    path = Path(rule_spec_path)
    if not path.exists():
        raise ValueError(f"Rule spec path does not exist: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"Rule spec is empty: {path}")
    rules = data.get("rules")
    if rules is None:
        raise ValueError(f"Rule spec missing 'rules' key: {path}")
    if not isinstance(rules, list):
        raise ValueError(f"Rule spec 'rules' must be a list: {path}")
    return list(rules)


def validate_rule_spec(rules: list[dict[str, Any]]) -> None:
    """
    Validate rule list. Raises ValueError on any violation.
    - Every rule has rule_id, enabled, priority, conditions
    - Every rule_id unique
    - Every operator in conditions is supported
    - Every severity in allowed set
    """
    if not rules:
        return
    seen_ids: set[str] = set()
    for r in rules:
        if not isinstance(r, dict):
            raise ValueError("Each rule must be a dict")
        rid = r.get("rule_id")
        if rid is None:
            raise ValueError("Every rule must have rule_id")
        if rid in seen_ids:
            raise ValueError(f"Duplicate rule_id: {rid}")
        seen_ids.add(rid)
        if "enabled" not in r:
            raise ValueError(f"Rule {rid}: missing 'enabled'")
        if "priority" not in r:
            raise ValueError(f"Rule {rid}: missing 'priority'")
        conds = r.get("conditions")
        if conds is None:
            raise ValueError(f"Rule {rid}: missing 'conditions'")
        if not isinstance(conds, dict):
            raise ValueError(f"Rule {rid}: conditions must be a dict (all/any)")
        sev = r.get("severity")
        if sev is not None and sev not in ALLOWED_SEVERITIES:
            raise ValueError(f"Rule {rid}: severity must be one of {sorted(ALLOWED_SEVERITIES)}, got {sev!r}")
        _validate_conditions(conds, rid)


def _validate_conditions(group: dict[str, Any], rule_id: str) -> None:
    """Validate one level of all/any and their condition list."""
    if set(group.keys()) - CONDITION_GROUPS:
        raise ValueError(f"Rule {rule_id}: conditions must use only 'all' or 'any'")
    for key in CONDITION_GROUPS:
        if key not in group:
            continue
        items = group[key]
        if not isinstance(items, list):
            raise ValueError(f"Rule {rule_id}: conditions.{key} must be a list")
        for c in items:
            if not isinstance(c, dict):
                raise ValueError(f"Rule {rule_id}: each condition must be a dict")
            if "fact" not in c or "op" not in c or "value" not in c:
                raise ValueError(f"Rule {rule_id}: each condition must have fact, op, value")
            if c["op"] not in SUPPORTED_OPS:
                raise ValueError(
                    f"Rule {rule_id}: unsupported operator {c['op']!r}, allowed: {sorted(SUPPORTED_OPS)}"
                )


def evaluate_condition(condition: dict[str, Any], facts: dict[str, Any]) -> bool:
    """
    Evaluate a single condition against facts.
    If fact key is missing from facts, returns False (no silent pass).
    """
    fact_name = condition.get("fact")
    op = condition.get("op")
    target = condition.get("value")
    if fact_name not in facts:
        return False
    actual = facts[fact_name]
    # Type-consistent comparison; allow numeric, str, bool, list
    if op == "eq":
        return actual == target
    if op == "ne":
        return actual != target
    if op == "gt":
        return _numeric(actual) > _numeric(target)
    if op == "gte":
        return _numeric(actual) >= _numeric(target)
    if op == "lt":
        return _numeric(actual) < _numeric(target)
    if op == "lte":
        return _numeric(actual) <= _numeric(target)
    if op == "in":
        return actual in (target if isinstance(target, (list, tuple)) else [target])
    if op == "not_in":
        return actual not in (target if isinstance(target, (list, tuple)) else [target])
    return False


def _numeric(x: Any) -> float:
    """Coerce to float for comparison; int stays exact where possible."""
    if isinstance(x, bool):
        raise TypeError("Cannot compare bool as number")
    if isinstance(x, int):
        return float(x)
    if isinstance(x, float):
        return x
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            raise TypeError(f"Cannot compare as number: {x!r}") from None
    raise TypeError(f"Cannot compare as number: {type(x)}")


def evaluate_condition_group(group: dict[str, Any], facts: dict[str, Any]) -> bool:
    """
    Evaluate one level of all/any. v1: single level only.
    Group must have exactly one of 'all' or 'any'; value is a list of conditions.
    """
    if "all" in group:
        for c in group["all"]:
            if not evaluate_condition(c, facts):
                return False
        return True
    if "any" in group:
        for c in group["any"]:
            if evaluate_condition(c, facts):
                return True
        return False
    return False  # empty or unknown group
