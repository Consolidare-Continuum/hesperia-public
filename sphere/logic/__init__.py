# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

# Layer-9 Logic Layer: rule-based reasoning over structural metrics.
from sphere.logic.rule_engine import evaluate_rules, compute_logic_metrics
from sphere.logic.rule_runtime import (
    load_rules,
    validate_rule_spec,
    evaluate_condition,
    evaluate_condition_group,
)
from sphere.logic.diagnostics import build_diagnostic, build_structural_diagnostics, build_logic_diagnostics
from sphere.logic.trigger_registry import build_rule_trigger_registry

__all__ = [
    "evaluate_rules",
    "compute_logic_metrics",
    "load_rules",
    "validate_rule_spec",
    "evaluate_condition",
    "evaluate_condition_group",
    "build_diagnostic",
    "build_structural_diagnostics",
    "build_logic_diagnostics",
    "build_rule_trigger_registry",
]
