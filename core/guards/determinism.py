"""Determinism guards and canonical hash checks."""

from __future__ import annotations

from core.diagnostics.determinism import canonical_json, deterministic_hash
from core.result.contract import validate_result_contract


def guard_determinism(result: dict) -> None:
    validate_result_contract(result)


__all__ = ["canonical_json", "deterministic_hash", "guard_determinism"]

