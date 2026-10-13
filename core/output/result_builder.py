"""Pure output builder for final canonical result."""

from __future__ import annotations

from typing import Any

from core.result.contract import build_result_contract, validate_result_contract


def build_result(
    *,
    area_activation: dict[str, float],
    family_activation: dict[str, float],
    trajectory: dict[str, Any],
    segment_drifts: list[float],
    failure_flags: list[str],
) -> dict[str, Any]:
    result = build_result_contract(
        area_activation=area_activation,
        family_activation=family_activation,
        trajectory=trajectory,
        segment_drifts=segment_drifts,
        failure_flags=failure_flags,
    ).to_dict()
    validate_result_contract(result)
    return result

