# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-9 Structural diagnostics: transform triggered rules into canonical diagnostic objects.
Deterministic, traceable to facts; machine-clean, no interpretation prose.
"""

from __future__ import annotations

from typing import Any


def build_diagnostic(triggered_rule: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    """
    Build one structural diagnostic from a triggered rule and current facts.
    Evidence is the subset of facts referenced by the rule (matched_facts if present, else key facts).
    """
    evidence = triggered_rule.get("matched_facts")
    if evidence is None:
        evidence = {}
    return {
        "rule_id": triggered_rule.get("rule_id", ""),
        "diagnostic_code": triggered_rule.get("diagnostic_code", ""),
        "severity": triggered_rule.get("severity", "medium"),
        "message": triggered_rule.get("diagnostic_message", ""),
        "evidence": dict(evidence),
    }


def build_structural_diagnostics(
    triggered_rules: list[dict[str, Any]],
    facts: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Build canonical structural diagnostics list from triggered rules, preserving order.
    Deterministic and traceable to triggering facts.
    """
    return [build_diagnostic(tr, facts) for tr in triggered_rules]


def build_logic_diagnostics(
    *,
    rules_evaluated_count: int = 0,
    rules_triggered_count: int = 0,
    dominant_area: int = 0,
    entropy_after_shadow: float = 0.0,
    tension_after_shadow: float = 0.0,
    propagation_spread: int = 0,
) -> dict[str, Any]:
    """Build logic_metrics diagnostics dict for Layer-9."""
    return {
        "rules_evaluated_count": rules_evaluated_count,
        "rules_triggered_count": rules_triggered_count,
        "dominant_area": dominant_area,
        "entropy_after_shadow": entropy_after_shadow,
        "tension_after_shadow": tension_after_shadow,
        "propagation_spread": propagation_spread,
    }
