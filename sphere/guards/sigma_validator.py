# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Sigma static invariant validator.
Enforces hard structural bounds, shape, mapping integrity. Deterministic, audit-friendly.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SPEC = _REPO_ROOT / "spec" / "sigma_invariants.yaml"


def _get_path(artifacts: dict[str, Any], target: str) -> Any:
    """Resolve target like raw_metrics.area_vector from artifacts."""
    parts = target.split(".")
    obj = artifacts
    for p in parts:
        if p not in obj:
            return None
        obj = obj[p]
    return obj


def _length_equals(val: Any, expected: int) -> bool:
    if val is None:
        return False
    if not isinstance(val, (list, tuple)):
        return False
    return len(val) == expected


def _matrix_12x12(val: Any) -> bool:
    if val is None:
        return False
    if not isinstance(val, (list, tuple)) or len(val) != 12:
        return False
    for row in val:
        if not isinstance(row, (list, tuple)) or len(row) != 12:
            return False
    return True


def _symmetric(val: Any) -> bool:
    if val is None or not _matrix_12x12(val):
        return False
    for i in range(12):
        for j in range(12):
            if val[i][j] != val[j][i]:
                return False
    return True


def _no_nan(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, (list, tuple)):
        return not any(isinstance(x, float) and math.isnan(x) for x in val)
    return not (isinstance(val, float) and math.isnan(val))


def _non_negative(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, (list, tuple)):
        return all(
            (isinstance(x, (int, float)) and x >= 0) or (not isinstance(x, (int, float)))
            for x in val
        )
    return isinstance(val, (int, float)) and val >= 0


def _in_closed_01(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return 0 <= val <= 1
    return False


def _scalar_or_object_in_01(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return 0 <= val <= 1
    if isinstance(val, dict) and "jump_rate" in val:
        return 0 <= val["jump_rate"] <= 1
    return False


def _area_id_valid(val: Any) -> bool:
    if val is None:
        return False
    return isinstance(val, (int, float)) and 0 <= int(val) < 12


def _run_check(
    invariant_id: str,
    name: str,
    artifacts: dict[str, Any],
    target: str | None,
    rule: str,
    expected: Any,
    optional_target: bool,
) -> tuple[bool, str | None]:
    """Run one invariant check. Return (passed, error_message)."""
    val = _get_path(artifacts, target) if target else None
    if val is None and optional_target:
        return True, None
    if val is None and target:
        return False, f"{target} missing"

    if rule == "length_equals":
        ok = _length_equals(val, expected)
        return ok, None if ok else f"length != {expected}"
    if rule == "matrix_12x12":
        ok = _matrix_12x12(val)
        return ok, None if ok else "matrix not 12x12"
    if rule == "symmetric":
        ok = _symmetric(val)
        return ok, None if ok else "matrix not symmetric"
    if rule == "no_nan":
        ok = _no_nan(val)
        return ok, None if ok else "NaN present"
    if rule == "non_negative":
        ok = _non_negative(val)
        return ok, None if ok else "negative value"
    if rule == "in_closed_01":
        ok = _in_closed_01(val)
        return ok, None if ok else "value not in [0,1]"
    if rule == "scalar_or_object_in_01":
        ok = _scalar_or_object_in_01(val)
        return ok, None if ok else "jump_rate not in [0,1]"
    if rule == "area_id_valid":
        ok = _area_id_valid(val)
        return ok, None if ok else "area id not in 0..11"
    raise ValueError(f"Unsupported Sigma rule: {rule!r}")


def validate_sigma_invariants(artifacts: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """
    Enforce static structural invariants. Returns passed, failed_checks, passed_checks.
    Malformed artifact paths produce structured failed check; unsupported rule raises ValueError.
    """
    spec_path = config.get("sigma_spec_path") or _DEFAULT_SPEC
    if spec_path and Path(spec_path).exists():
        with open(spec_path, encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        invariants = spec.get("invariants", [])
    else:
        invariants = _builtin_sigma_invariants()

    # Normalize artifacts: support both flat and nested (raw_metrics under artifacts or at top)
    if "raw_metrics" not in artifacts and "usf" in artifacts:
        usf = artifacts.get("usf") or {}
        artifacts = {
            "raw_metrics": usf.get("raw_metrics", {}),
            "dynamism_metrics": usf.get("dynamism_metrics", {}),
            "propagation_metrics": usf.get("propagation_metrics", {}),
            "logic_outputs": usf.get("logic_outputs", {}),
            "topology": artifacts.get("topology", {}),
        }
    if "propagation_metrics" not in artifacts and "propagated_area_vector" in artifacts:
        artifacts.setdefault("propagation_metrics", {
            "propagated_area_vector": artifacts.get("propagated_area_vector"),
            "propagated_family_counts": artifacts.get("propagated_family_counts"),
        })

    passed_checks: list[str] = []
    failed_checks: list[dict[str, Any]] = []

    for inv in invariants:
        if inv.get("enabled") is not True:
            continue
        inv_id = inv.get("invariant_id", "")
        name = inv.get("name", inv_id)
        target = inv.get("target")
        rule = inv.get("rule", "")
        expected = inv.get("expected")
        optional = inv.get("optional_target", False)
        try:
            ok, msg = _run_check(inv_id, name, artifacts, target, rule, expected, optional)
            if ok:
                passed_checks.append(inv_id)
            else:
                failed_checks.append({
                    "invariant_id": inv_id,
                    "message": msg or f"{name} failed",
                })
        except ValueError as e:
            failed_checks.append({"invariant_id": inv_id, "message": str(e)})

    return {
        "passed": len(failed_checks) == 0,
        "failed_checks": failed_checks,
        "passed_checks": passed_checks,
    }


def _builtin_sigma_invariants() -> list[dict[str, Any]]:
    """Fallback when spec file missing."""
    return [
        {"invariant_id": "SIGMA_001", "name": "area_vector_len_12", "target": "raw_metrics.area_vector", "rule": "length_equals", "expected": 12},
        {"invariant_id": "SIGMA_002", "name": "family_counts_len_288", "target": "raw_metrics.family_counts", "rule": "length_equals", "expected": 288},
        {"invariant_id": "SIGMA_005", "name": "propagated_area_vector_len_12", "target": "propagation_metrics.propagated_area_vector", "rule": "length_equals", "expected": 12},
        {"invariant_id": "SIGMA_006", "name": "propagated_family_counts_len_288", "target": "propagation_metrics.propagated_family_counts", "rule": "length_equals", "expected": 288},
        {"invariant_id": "SIGMA_007", "name": "transition_matrix_12x12", "target": "dynamism_metrics.transition_matrix", "rule": "matrix_12x12"},
        {"invariant_id": "SIGMA_009", "name": "area_vector_no_nan", "target": "raw_metrics.area_vector", "rule": "no_nan"},
        {"invariant_id": "SIGMA_010", "name": "family_counts_non_negative", "target": "raw_metrics.family_counts", "rule": "non_negative"},
        {"invariant_id": "SIGMA_011", "name": "coverage_in_01", "target": "raw_metrics.coverage", "rule": "in_closed_01"},
        {"invariant_id": "SIGMA_012", "name": "jump_rate_in_01", "target": "dynamism_metrics.jump_rate", "rule": "scalar_or_object_in_01"},
        {"invariant_id": "SIGMA_013", "name": "stability_index_in_01", "target": "dynamism_metrics.stability_index", "rule": "in_closed_01"},
        {"invariant_id": "SIGMA_014", "name": "loopability_in_01", "target": "raw_metrics.loopability", "rule": "in_closed_01"},
        {"invariant_id": "SIGMA_015", "name": "area_ids_in_0_11", "target": "raw_metrics.dominant_area", "rule": "area_id_valid"},
    ]
