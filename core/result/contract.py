"""Canonical Hesperia execution contract and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.diagnostics.determinism import deterministic_hash
from core.dynamics.numeric import EPS, clamp01, quantize

SCHEMA_VERSION = "hesperia.result.v1"
AREA_COUNT = 12
FAMILY_COUNT = 24


@dataclass(frozen=True)
class HesperiaResult:
    area_vector: list[float]
    family_vector: list[float]
    dominant_area: int
    dominant_family: int
    tension: float
    loopability: float
    stability: float
    failure_flags: list[str]
    schema_version: str
    fingerprint: str
    deterministic_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "area_vector": list(self.area_vector),
            "family_vector": list(self.family_vector),
            "dominant_area": int(self.dominant_area),
            "dominant_family": int(self.dominant_family),
            "tension": float(self.tension),
            "loopability": float(self.loopability),
            "stability": float(self.stability),
            "failure_flags": list(self.failure_flags),
            "schema_version": self.schema_version,
            "fingerprint": self.fingerprint,
            "deterministic_hash": self.deterministic_hash,
        }


def _normalize_vector(values: list[float], size: int) -> list[float]:
    vec = [max(0.0, float(x)) for x in values[:size]]
    if len(vec) < size:
        vec.extend([0.0] * (size - len(vec)))
    total = sum(vec)
    if total <= EPS:
        return [quantize(1.0 / size) for _ in range(size)]
    return [quantize(v / total) for v in vec]


def _argmax_with_confidence(vec: list[float]) -> tuple[int, float]:
    ranked = sorted(enumerate(vec), key=lambda it: (-it[1], it[0]))
    top_idx, top_val = ranked[0]
    second_val = ranked[1][1] if len(ranked) > 1 else 0.0
    return int(top_idx), quantize(max(0.0, top_val - second_val))


def compute_tension(area_vector: list[float]) -> float:
    pairs = [(i, i + 6) for i in range(6)]
    return quantize(sum(abs(float(area_vector[a]) - float(area_vector[b])) for a, b in pairs))


def compute_loopability(trajectory: dict[str, Any]) -> float:
    transition_count = float(trajectory.get("transition_count", 0.0))
    segment_count = max(1.0, float(trajectory.get("segment_count", 1.0)))
    stability_window = clamp01(float(trajectory.get("stability_window", 0.0)))
    return_frequency = clamp01(1.0 - (transition_count / max(1.0, segment_count - 1.0)))
    cycle_detection = clamp01(1.0 - min(1.0, float(trajectory.get("jump_distance", 0.0)) / 24.0))
    return quantize((return_frequency + cycle_detection + stability_window) / 3.0)


def compute_stability(segment_drifts: list[float]) -> float:
    if not segment_drifts:
        return 1.0
    mean = sum(segment_drifts) / len(segment_drifts)
    variance = sum((d - mean) ** 2 for d in segment_drifts) / len(segment_drifts)
    return quantize(clamp01(1.0 - variance))


def build_result_contract(
    *,
    area_activation: dict[str, float],
    family_activation: dict[str, float],
    trajectory: dict[str, Any],
    segment_drifts: list[float],
    failure_flags: list[str],
) -> HesperiaResult:
    area_raw = [float(area_activation.get(f"A{i + 1}", 0.0)) for i in range(AREA_COUNT)]
    family_raw = [float(family_activation.get(f"F{i + 1}", 0.0)) for i in range(FAMILY_COUNT)]
    area_vector = _normalize_vector(area_raw, AREA_COUNT)
    family_vector = _normalize_vector(family_raw, FAMILY_COUNT)
    dominant_area, _ = _argmax_with_confidence(area_vector)
    dominant_family, _ = _argmax_with_confidence(family_vector)
    tension = compute_tension(area_vector)
    loopability = compute_loopability(trajectory)
    stability = compute_stability(segment_drifts)
    payload = {
        "area_vector": area_vector,
        "family_vector": family_vector,
        "dominant_area": dominant_area,
        "dominant_family": dominant_family,
        "tension": tension,
        "loopability": loopability,
        "stability": stability,
        "failure_flags": sorted(set(failure_flags)),
        "schema_version": SCHEMA_VERSION,
    }
    fingerprint = deterministic_hash(
        {
            "area_vector": area_vector,
            "family_vector": family_vector,
            "dominant_area": dominant_area,
            "tension": tension,
        }
    )
    payload["fingerprint"] = fingerprint
    payload["deterministic_hash"] = deterministic_hash(payload)
    return HesperiaResult(**payload)


def validate_result_contract(result: dict[str, Any]) -> None:
    expected = {
        "area_vector",
        "family_vector",
        "dominant_area",
        "dominant_family",
        "tension",
        "loopability",
        "stability",
        "failure_flags",
        "schema_version",
        "fingerprint",
        "deterministic_hash",
    }
    if set(result.keys()) != expected:
        raise ValueError("result_schema_mismatch")
    if result["schema_version"] != SCHEMA_VERSION:
        raise ValueError("result_schema_version_mismatch")
    area_sum = float(sum(result["area_vector"]))
    family_sum = float(sum(result["family_vector"]))
    if abs(area_sum - 1.0) > 1e-6 or abs(family_sum - 1.0) > 1e-6:
        raise ValueError("result_normalization_failed")
    for vec_name in ("area_vector", "family_vector"):
        for val in result[vec_name]:
            if val < -EPS or val > 1.0 + EPS:
                raise ValueError("result_bounds_failed")
    payload = {k: v for k, v in result.items() if k != "deterministic_hash"}
    if deterministic_hash(payload) != result["deterministic_hash"]:
        raise ValueError("result_determinism_failed")

