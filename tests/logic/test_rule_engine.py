# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Tests for rule engine (evaluate_rules).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_rule_trigger_structural_monotony() -> None:
    """Facts with entropy < 0.35 trigger STRUCTURAL_MONOTONY."""
    from sphere.logic import evaluate_rules
    facts = {"entropy": 0.22, "coverage": 0.5}
    out = evaluate_rules(facts)
    codes = [r.get("diagnostic_code") for r in out["triggered_rules"]]
    assert "STRUCTURAL_MONOTONY" in codes


def test_rule_trigger_deterministic() -> None:
    """Same facts produce same triggered_rules order and content."""
    from sphere.logic import evaluate_rules
    facts = {"entropy": 0.2, "coverage": 0.1, "curvature": 1.3, "stability_index": 0.1}
    a = evaluate_rules(facts)
    b = evaluate_rules(facts)
    assert a["triggered_rules"] == b["triggered_rules"]
