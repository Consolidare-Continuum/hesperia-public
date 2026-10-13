# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Tests for trigger registry (count, by_severity, by_code).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_registry_count_matches_triggered_rules() -> None:
    """rule_trigger_registry.count == len(triggered_rules)."""
    from sphere.logic import evaluate_rules
    out = evaluate_rules({"entropy": 0.2, "coverage": 0.5})
    assert out["rule_trigger_registry"]["count"] == len(out["triggered_rules"])


def test_registry_by_code() -> None:
    """by_code lists diagnostic_code counts."""
    from sphere.logic import evaluate_rules
    out = evaluate_rules({"entropy": 0.2})
    by_code = out["rule_trigger_registry"]["by_code"]
    assert isinstance(by_code, dict)
    assert sum(by_code.values()) == len(out["triggered_rules"])
