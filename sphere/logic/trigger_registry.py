# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-9 Rule trigger registry: which rules fired, in what order, and summary by severity/code.
Deterministic ordering (priority descending, rule_id ascending tie-break).
"""

from __future__ import annotations

from typing import Any

ALLOWED_SEVERITIES = ("low", "medium", "high", "critical")


def build_rule_trigger_registry(
    triggered_rules: list[dict[str, Any]],
    facts: dict[str, Any],
) -> dict[str, Any]:
    """
    Build canonical registry of triggered rules.
    Order preserved from triggered_rules (already sorted by engine).
    """
    triggered_rule_ids = [r.get("rule_id", "") for r in triggered_rules]
    by_severity = {s: 0 for s in ALLOWED_SEVERITIES}
    by_code: dict[str, int] = {}
    for r in triggered_rules:
        sev = r.get("severity", "medium")
        if sev in by_severity:
            by_severity[sev] += 1
        code = r.get("diagnostic_code", "")
        by_code[code] = by_code.get(code, 0) + 1
    return {
        "triggered_rule_ids": triggered_rule_ids,
        "count": len(triggered_rules),
        "by_severity": by_severity,
        "by_code": by_code,
    }
