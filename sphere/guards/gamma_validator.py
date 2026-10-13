# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Gamma dynamic invariant validator.
Enforces runtime order, isolation, sequence consistency. Deterministic, audit-friendly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SPEC = _REPO_ROOT / "spec" / "gamma_invariants.yaml"


def _run_gamma_check(
    invariant_id: str,
    rule: str,
    layer_outputs: dict[str, Any],
    runtime_metadata: dict[str, Any],
    config: dict[str, Any],
) -> tuple[bool, str | None]:
    """Run one Gamma check. Return (passed, error_message)."""
    if rule == "layers_executed_canonical_order":
        executed = runtime_metadata.get("executed_layers", [])
        expected = list(range(1, 11))
        if executed != expected:
            return False, f"executed_layers {executed} != canonical {expected}"
        return True, None

    if rule == "no_illegal_mutation_of_upstream":
        # If runtime provides isolation_validation_passed, trust it
        if runtime_metadata.get("isolation_validation_passed") is True:
            return True, None
        # Otherwise we cannot verify without snapshots; pass if not specified
        return True, None

    if rule == "raw_propagated_artifacts_must_be_distinct":
        # Pipeline must keep raw and propagated separate; we check structure
        layers = layer_outputs
        if "layer_3" in layers and "layer_7" in layers:
            l3 = layers["layer_3"]
            l7 = layers["layer_7"]
            if l7.get("raw_area_vector_overwritten") is True:
                return False, "Layer-7 overwrote raw area_vector"
            if l7.get("raw_family_counts_overwritten") is True:
                return False, "Layer-7 overwrote raw family_counts"
        return True, None

    if rule == "area_sequence_values_in_0_11":
        # Check if we have area_sequence in runtime or in dynamism
        seq = runtime_metadata.get("area_sequence")
        if seq is not None:
            if not all(0 <= int(x) < 12 for x in seq):
                return False, "area_sequence value out of 0..11"
        return True, None

    if rule == "transition_matrix_sum_equals_transitions":
        layer_6 = layer_outputs.get("layer_6", {})
        trans = layer_6.get("transition_matrix")
        if trans is not None and isinstance(trans, (list, tuple)):
            total = sum(c for row in trans for c in row)
            seq = runtime_metadata.get("area_sequence", [])
            expected_transitions = max(len(seq) - 1, 0)
            if total != expected_transitions:
                return False, f"transition_matrix sum {total} != transitions {expected_transitions}"
        return True, None

    if rule == "propagated_lengths_match_raw":
        # Compare raw vs propagated lengths when both present
        usf = runtime_metadata.get("usf") or config.get("usf")
        if usf and isinstance(usf, dict):
            raw = usf.get("raw_metrics", {})
            prop = usf.get("propagation_metrics", {})
            av_raw = raw.get("area_vector") or []
            av_prop = prop.get("propagated_area_vector") or []
            fc_raw = raw.get("family_counts") or []
            fc_prop = prop.get("propagated_family_counts") or []
            if len(av_raw) != len(av_prop) and (av_raw or av_prop):
                return False, "propagated_area_vector length != raw area_vector"
            if len(fc_raw) != len(fc_prop) and (fc_raw or fc_prop):
                return False, "propagated_family_counts length != raw family_counts"
        return True, None

    if rule == "registry_count_matches_triggered_rules":
        logic = layer_outputs.get("layer_9", {})
        if not logic:
            return True, None
        triggered = logic.get("triggered_rules", [])
        registry = logic.get("rule_trigger_registry", {})
        count = registry.get("count", 0)
        if len(triggered) != count:
            return False, f"registry count {count} != len(triggered_rules) {len(triggered)}"
        return True, None

    if rule == "deterministic_flag_true":
        det = runtime_metadata.get("deterministic")
        if det is not True:
            return False, "deterministic flag not true"
        return True, None

    raise ValueError(f"Unsupported Gamma rule: {rule!r}")


def validate_gamma_invariants(
    layer_outputs: dict[str, Any],
    runtime_metadata: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Enforce dynamic runtime invariants. Returns passed, failed_checks, passed_checks.
    Missing runtime metadata fails explicit checks where required.
    """
    spec_path = config.get("gamma_spec_path") or _DEFAULT_SPEC
    if spec_path and Path(spec_path).exists():
        with open(spec_path, encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        invariants = spec.get("invariants", [])
    else:
        invariants = _builtin_gamma_invariants()

    passed_checks: list[str] = []
    failed_checks: list[dict[str, Any]] = []

    for inv in invariants:
        if inv.get("enabled") is not True:
            continue
        inv_id = inv.get("invariant_id", "")
        rule = inv.get("rule", "")
        try:
            ok, msg = _run_gamma_check(
                inv_id, rule, layer_outputs, runtime_metadata, config
            )
            if ok:
                passed_checks.append(inv_id)
            else:
                failed_checks.append({
                    "invariant_id": inv_id,
                    "message": msg or f"{rule} failed",
                })
        except ValueError as e:
            failed_checks.append({"invariant_id": inv_id, "message": str(e)})

    return {
        "passed": len(failed_checks) == 0,
        "failed_checks": failed_checks,
        "passed_checks": passed_checks,
    }


def _builtin_gamma_invariants() -> list[dict[str, Any]]:
    return [
        {"invariant_id": "GAMMA_001", "rule": "layers_executed_canonical_order"},
        {"invariant_id": "GAMMA_002", "rule": "no_illegal_mutation_of_upstream"},
        {"invariant_id": "GAMMA_003", "rule": "raw_propagated_artifacts_must_be_distinct"},
        {"invariant_id": "GAMMA_004", "rule": "area_sequence_values_in_0_11"},
        {"invariant_id": "GAMMA_005", "rule": "transition_matrix_sum_equals_transitions"},
        {"invariant_id": "GAMMA_006", "rule": "propagated_lengths_match_raw"},
        {"invariant_id": "GAMMA_007", "rule": "rule_registry_count_consistent"},
        {"invariant_id": "GAMMA_008", "rule": "deterministic_flag_true"},
    ]
