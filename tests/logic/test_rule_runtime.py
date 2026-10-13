# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Tests for rule runtime (load_rules, validate_rule_spec, evaluate_condition).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_load_rules_from_spec() -> None:
    """load_rules returns list of rules from spec."""
    from sphere.logic import load_rules
    path = _REPO / "spec" / "logic_rules.yaml"
    rules = load_rules(path)
    assert isinstance(rules, list)
    assert len(rules) >= 1
    assert "rule_id" in rules[0]
    assert "conditions" in rules[0]


def test_evaluate_condition_lt() -> None:
    """evaluate_condition(entropy lt 0.35) with facts."""
    from sphere.logic import evaluate_condition
    cond = {"fact": "entropy", "op": "lt", "value": 0.35}
    assert evaluate_condition(cond, {"entropy": 0.22}) is True
    assert evaluate_condition(cond, {"entropy": 0.5}) is False


def test_evaluate_condition_missing_fact() -> None:
    """Missing fact returns False (no silent pass)."""
    from sphere.logic import evaluate_condition
    cond = {"fact": "entropy", "op": "lt", "value": 0.35}
    assert evaluate_condition(cond, {}) is False
