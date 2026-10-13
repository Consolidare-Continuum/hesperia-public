# HESPERIA — hesperia-dev-test math compliance. Copyright © 2026 igareosh.com.
"""Fast, in-process, no-semantic-read compliance checks: finiteness, ranges, vector-length
contracts, required contract keys and types. Never interprets what a value means — only that it
is well-formed (ADV-09: witness of structural equality, not an oracle of domain truth).
"""

from __future__ import annotations

import math
from typing import Any

_REQUIRED_ANALYZE_TOP_KEYS = (
    "L1",
    "L2",
    "L3",
    "L4",
    "L5",
    "L6",
    "L7",
    "L8",
    "L9",
    "multiscale_signals",
    "engine_result",
    "system_version",
    "schema_version",
)

# Colombo Bench-0 §4.2 — presence + type only; values pinned separately (gold.py) where stable.
_L1_SCALAR_ALLOWLIST: dict[str, type] = {
    "TOTAL_TOKENS": int,
    "COVERAGE_RATIO": float,
    "UNIQUE_FAMILIES_HIT": int,
    "CANONICAL_PIPELINE": str,
    "CALIBRATION_FALLBACK_USED": str,
}

_GROUND_TRUTH_AXES = ("logical", "weight", "source_activation")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_no_nan_inf(obj: Any, path: str = "$") -> list[str]:
    """Recursively reject NaN/Inf anywhere in a response body — hard fail, no exceptions."""
    violations: list[str] = []
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            violations.append(f"{path}: non-finite float {obj}")
    elif isinstance(obj, dict):
        for key, value in obj.items():
            violations.extend(check_no_nan_inf(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            violations.extend(check_no_nan_inf(value, f"{path}[{i}]"))
    return violations


def check_vector_lengths(multiscale_signals: dict[str, Any]) -> list[str]:
    """SIGMA/ontology grain: family_activation_vector==288, area_activation_vector==12."""
    violations: list[str] = []
    fav = multiscale_signals.get("family_activation_vector") or []
    aav = multiscale_signals.get("area_activation_vector") or []
    if len(fav) != 288:
        violations.append(f"family_activation_vector length {len(fav)} != 288")
    if len(aav) != 12:
        violations.append(f"area_activation_vector length {len(aav)} != 12")
    return violations


def check_l1_scalar_allowlist(l1: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for key, expected_type in _L1_SCALAR_ALLOWLIST.items():
        if key not in l1:
            violations.append(f"L1 missing {key!r}")
            continue
        value = l1[key]
        if expected_type is float and _is_number(value):
            continue
        if expected_type is int and isinstance(value, int) and not isinstance(value, bool):
            continue
        if expected_type is str and isinstance(value, str):
            continue
        violations.append(
            f"L1[{key!r}] wrong type: {type(value).__name__}, expected {expected_type.__name__}"
        )
    return violations


def check_activation_ranges(trace: list[dict[str, Any]]) -> list[str]:
    """activation/confidence must be finite and in [0, 1] where present."""
    violations: list[str] = []
    for i, step in enumerate(trace):
        for key in ("activation", "confidence"):
            value = step.get(key)
            if value is None:
                continue
            if not _is_number(value):
                violations.append(f"trace[{i}].{key} not numeric: {value!r}")
                continue
            fvalue = float(value)
            if math.isnan(fvalue) or math.isinf(fvalue):
                violations.append(f"trace[{i}].{key} non-finite: {value}")
            elif not (0.0 <= fvalue <= 1.0):
                violations.append(f"trace[{i}].{key} out of [0,1]: {value}")
    return violations


def check_analyze_contract(analyze_body: dict[str, Any]) -> list[str]:
    """Required top-level keys on POST /analyze — presence only, no value judgment."""
    return [f"/analyze missing top-level key {key!r}" for key in _REQUIRED_ANALYZE_TOP_KEYS if key not in analyze_body]


def check_interpret_contract(interpret_body: dict[str, Any]) -> list[str]:
    """Required schema/ground_truth/router_envelope contract on POST /product/interpret."""
    violations: list[str] = []
    gt = interpret_body.get("ground_truth") or {}
    for axis in _GROUND_TRUTH_AXES:
        if axis not in gt:
            violations.append(f"/product/interpret ground_truth missing axis {axis!r}")
    if "router_envelope" not in interpret_body:
        violations.append("/product/interpret missing router_envelope")
    return violations
