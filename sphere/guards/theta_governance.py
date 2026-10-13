# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Theta governance rule layer.
Gates canonical output eligibility; classifies violations; no free-form eval.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SPEC = _REPO_ROOT / "spec" / "theta_governance_rules.yaml"


def _eval_condition(condition: dict[str, Any], facts: dict[str, Any]) -> bool:
    """Evaluate condition (all/any with fact/op/value). Deterministic; no eval."""
    if "all" in condition:
        for c in condition["all"]:
            fact_name = c.get("fact")
            op = c.get("op")
            value = c.get("value")
            if fact_name not in facts:
                return False
            actual = facts[fact_name]
            if op == "eq":
                if actual != value:
                    return False
            elif op == "ne":
                if actual == value:
                    return False
            else:
                return False
        return True
    if "any" in condition:
        for c in condition["any"]:
            fact_name = c.get("fact")
            op = c.get("op")
            value = c.get("value")
            if fact_name not in facts:
                continue
            actual = facts[fact_name]
            if op == "eq" and actual == value:
                return True
            if op == "ne" and actual != value:
                return True
        return False
    return False


def _build_governance_facts(
    artifacts: dict[str, Any],
    sigma_result: dict[str, Any],
    gamma_result: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build fact dict for Theta rule evaluation."""
    facts: dict[str, Any] = {
        "sigma_passed": sigma_result.get("passed") is True,
        "gamma_passed": gamma_result.get("passed") is True,
        "raw_artifact_mutation": False,
        "has_usf": False,
        "has_raw_metrics": False,
        "has_logic_outputs": False,
        "has_provenance": False,
        "layer10_placeholder": False,
        "deterministic": False,
    }
    art = artifacts
    if "usf" in art and isinstance(art["usf"], dict) and "_usf_error" not in art["usf"]:
        facts["has_usf"] = True
        usf = art["usf"]
        facts["has_raw_metrics"] = "raw_metrics" in usf and isinstance(usf["raw_metrics"], dict)
        facts["has_logic_outputs"] = "logic_outputs" in usf and isinstance(usf["logic_outputs"], dict)
        facts["has_provenance"] = "provenance" in usf and isinstance(usf["provenance"], dict)
        facts["deterministic"] = usf.get("provenance", {}).get("deterministic") is True
    if "layer_outputs" in art:
        l10 = art["layer_outputs"].get("layer_10", {})
        facts["layer10_placeholder"] = l10.get("_placeholder") is True
    if not facts["deterministic"] and config.get("deterministic") is True:
        facts["deterministic"] = True
    return facts


def evaluate_theta_governance(
    artifacts: dict[str, Any],
    sigma_result: dict[str, Any],
    gamma_result: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate governance rules. Returns approved, status, violations, warnings, governance_flags.
    Unsupported action raises ValueError. Rules are deterministic and declarative.
    """
    spec_path = config.get("theta_spec_path") or _DEFAULT_SPEC
    if spec_path and Path(spec_path).exists():
        with open(spec_path, encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        rules = spec.get("rules", [])
    else:
        rules = _builtin_theta_rules()

    facts = _build_governance_facts(artifacts, sigma_result, gamma_result, config)
    violations: list[dict[str, Any]] = []
    warnings: list[str] = []
    governance_flags: list[str] = []
    approved = True
    status = "canonical"

    for rule in rules:
        if rule.get("enabled") is not True:
            continue
        rule_id = rule.get("rule_id", "")
        condition = rule.get("condition", {})
        action = rule.get("action", "")
        message = rule.get("message", "")
        fail_message = rule.get("fail_message", message)
        severity = rule.get("severity", "high")

        cond_met = _eval_condition(condition, facts)
        if action == "approve_canonical":
            if not cond_met:
                approved = False
                status = "quarantined"
                violations.append({
                    "rule_id": rule_id,
                    "severity": severity,
                    "message": fail_message or message,
                })
                if "NON_CANONICAL_OUTPUT" not in governance_flags:
                    governance_flags.append("NON_CANONICAL_OUTPUT")
        elif action == "flag_non_canonical_interpretation":
            if cond_met:
                warnings.append(message)
                governance_flags.append("NON_CANONICAL_INTERPRETATION")
        else:
            raise ValueError(f"Unsupported Theta action: {action!r}")

    return {
        "approved": approved,
        "status": status,
        "violations": violations,
        "warnings": warnings,
        "governance_flags": governance_flags,
    }


def _builtin_theta_rules() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "THETA_001",
            "enabled": True,
            "severity": "critical",
            "condition": {
                "all": [
                    {"fact": "sigma_passed", "op": "eq", "value": True},
                    {"fact": "gamma_passed", "op": "eq", "value": True},
                ]
            },
            "action": "approve_canonical",
            "message": "Canonical output requires Sigma and Gamma pass.",
        },
        {
            "rule_id": "THETA_002",
            "enabled": True,
            "severity": "critical",
            "condition": {"all": [{"fact": "raw_artifact_mutation", "op": "eq", "value": False}]},
            "action": "approve_canonical",
            "fail_message": "Raw structural artifacts differ from locked measurement snapshots.",
        },
        {
            "rule_id": "THETA_003",
            "enabled": True,
            "severity": "critical",
            "condition": {
                "all": [
                    {"fact": "has_usf", "op": "eq", "value": True},
                    {"fact": "has_raw_metrics", "op": "eq", "value": True},
                    {"fact": "has_logic_outputs", "op": "eq", "value": True},
                    {"fact": "has_provenance", "op": "eq", "value": True},
                ]
            },
            "action": "approve_canonical",
            "message": "Required artifacts (USF, raw_metrics, logic_outputs, provenance) must be present.",
        },
        {
            "rule_id": "THETA_004",
            "enabled": True,
            "severity": "medium",
            "condition": {"any": [{"fact": "layer10_placeholder", "op": "eq", "value": True}]},
            "action": "flag_non_canonical_interpretation",
            "message": "Placeholder Layer-10 cannot upgrade output to canonical narrative truth.",
        },
        {
            "rule_id": "THETA_005",
            "enabled": True,
            "severity": "critical",
            "condition": {"all": [{"fact": "deterministic", "op": "eq", "value": True}]},
            "action": "approve_canonical",
            "message": "Deterministic flag must be true for canonical output.",
        },
    ]
