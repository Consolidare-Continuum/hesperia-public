# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Unit tests for logic layer (sphere.logic).
Verifies rule evaluation, triggered rules, diagnostics, registry.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_rule_trigger_structural_monotony() -> None:
    """Low entropy triggers STRUCTURAL_MONOTONY diagnostic code."""
    from sphere.logic import evaluate_rules
    facts = {"entropy": 0.2, "coverage": 0.5, "dominant_area": 0, "dominant_family": 0}
    out = evaluate_rules(facts)
    codes = [r.get("diagnostic_code") for r in out["triggered_rules"]]
    assert "STRUCTURAL_MONOTONY" in codes


def test_rule_trigger_deterministic() -> None:
    """Same facts produce same triggered rules."""
    from sphere.logic import evaluate_rules
    facts = {"entropy": 0.4, "coverage": 0.6, "curvature": 0.8, "stability_index": 0.5}
    a = evaluate_rules(facts)
    b = evaluate_rules(facts)
    assert [r.get("rule_id") for r in a["triggered_rules"]] == [r.get("rule_id") for r in b["triggered_rules"]]


def test_registry_count_matches_triggered() -> None:
    """rule_trigger_registry count equals len(triggered_rules)."""
    from sphere.logic import evaluate_rules
    facts = {"entropy": 0.22, "coverage": 0.1, "curvature": 1.3, "stability_index": 0.1}
    out = evaluate_rules(facts)
    assert out["rule_trigger_registry"]["count"] == len(out["triggered_rules"])
