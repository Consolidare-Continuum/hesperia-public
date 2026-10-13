# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Engine 0.5.0 — Layer-6 (39_SPEC); “v0.4.x” = legacy SPEC-era label only.
25 variables: sensitivity, curvature, rank, depth growth, Lyapunov, stability.
Inputs: L1, L2 (with MASS_AT_DEPTH); when no perturbation, stub with 0/1.0.
Downstream: L7 (CONSIST_STABILITY_REGIME_VALID, MAX_CHAOS_LEVEL), L8 (SI_GLOBAL_STABILITY), L9.

HES-MATH-BEHAV-54..57 (2026-08-05): gradient / curvature / Group-IV Newtonian +
functional slots use a caller-supplied E(x±ε) series only when explicitly enabled.
Without that opt-in series they stay at sealed identity constants. Do not invent
finite-difference values from MASS_AT_DEPTH alone. Formula notes live next to each
assignment below.
"""

from __future__ import annotations

import math
import time
from typing import Any

from core.contracts.layer_contract import LayerInput, LayerOutput

eps = 1e-12

# Reserved slots that remain PARTIAL without perturbation series (inventory HES-MATH-BEHAV-54).
L6_PARTIAL_GRADIENT_SLOTS = (
    "COVERAGE_GRADIENT",
    "ENTROPY_GRADIENT",
)
L6_PARTIAL_CURVATURE_SLOTS = (
    "SECOND_ORDER_RESPONSE",
    "DOMINANCE_CURVATURE",
    "ENTROPY_CURVATURE",
)
L6_PARTIAL_GROUP_IV_SLOTS = (
    "POTENTIAL_GRADIENT",
    "ESCAPE_ENERGY_THRESHOLD",
    "FORCE_ANALOG_MAGNITUDE",
    "MONOTONICITY_CHECK",
    "FIXED_POINT_DETECTION",
    "CYCLE_DETECTION_FUNCTIONAL",
)


def _numeric(mapping: dict[str, Any], key: str) -> float | None:
    value = mapping.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _vector(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or not value:
        return None
    if not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
        return None
    return [float(item) for item in value]


def _same_length_vectors(*vectors: list[float] | None) -> bool:
    return all(vector is not None for vector in vectors) and len({len(vector) for vector in vectors if vector is not None}) == 1


def _difference_norm(left: list[float], right: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def _vectors_close(left: list[float], right: list[float], tolerance: float) -> bool:
    return _same_length_vectors(left, right) and all(
        abs(a - b) <= tolerance for a, b in zip(left, right)
    )


def _snapshot_l1(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {}
    candidate = snapshot.get("l1")
    return candidate if isinstance(candidate, dict) else {}


def _perturbation_points(
    base_l1: dict[str, Any],
    series: dict[str, Any],
    epsilon_magnitude: float,
) -> list[tuple[float, dict[str, Any], float | None]]:
    points: list[tuple[float, dict[str, Any], float | None]] = []
    for direction in ("minus", "plus"):
        snapshot = series.get(direction)
        if not isinstance(snapshot, dict):
            continue
        intensity = _numeric(snapshot, "input_intensity")
        points.append((epsilon_magnitude, _snapshot_l1(snapshot), intensity))
    samples = series.get("samples")
    if isinstance(samples, list):
        for snapshot in samples:
            if not isinstance(snapshot, dict):
                continue
            magnitude = _numeric(snapshot, "epsilon_magnitude")
            if magnitude is None or magnitude < 0.0:
                continue
            intensity = _numeric(snapshot, "input_intensity")
            points.append((magnitude, _snapshot_l1(snapshot), intensity))
    base_intensity = _numeric(series, "base_input_intensity")
    if base_intensity is not None:
        points.append((0.0, base_l1, base_intensity))
    return points


def compute_L6(
    l1: dict[str, Any],
    l2: dict[str, Any],
    mass_at_depth: list[float] | None = None,
    F: int = 288,
    eps_val: float = eps,
    perturbation_enabled: bool = False,
    perturbation_series: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Compute Layer-6 25 variables (39_SPEC).
    The optional perturbation_series is a minimal hook for already-computed E(x±ε)
    snapshots. It is ignored unless perturbation_enabled=True, keeping /analyze and
    all existing callers sealed by default. Snapshot scalar metrics use Layer-1 keys;
    vector formulas require explicit ``output`` / ``base_output`` arrays.

    Without an enabled, sufficient series: INPUT_PERTURBATION_RESPONSE=0,
    DOMINANT_FAMILY_STABILITY=True, gradients/curvature/rank/condition/spectral_gap
    are 0 or 1.0; depth growth still comes from mass_at_depth when provided.
    LYAPUNOV_ESTIMATE = 0.0 (stable); GLOBAL_STABILITY_SCORE = 1.0; CONCEPTUAL_COHERENCE_INDEX from L1/L2.
    """
    mass_at_depth = mass_at_depth or l2.get("MASS_AT_DEPTH") or [0.0]
    norm_entropy = float(l1.get("NORMALIZED_FAMILY_ENTROPY", 0.0))

    # I. No perturbation → 0 or identity (sealed safe defaults)
    INPUT_PERTURBATION_RESPONSE = 0.0
    DOMINANT_FAMILY_STABILITY = True
    # PARTIAL (HES-MATH-BEHAV-55): 39_SPEC (coverage(x+ε)-coverage(x))/(‖ε‖+eps) — needs E(x+ε).
    COVERAGE_GRADIENT = 0.0
    # PARTIAL (HES-MATH-BEHAV-55): 39_SPEC (entropy(x+ε)-entropy(x))/(‖ε‖+eps) — needs E(x+ε).
    ENTROPY_GRADIENT = 0.0
    STABILITY_RADIUS = 1.0
    # PARTIAL (HES-MATH-BEHAV-56): 39_SPEC (y(x+ε)-2y(x)+y(x-ε))/(‖ε‖²+eps) — needs ±ε runs.
    SECOND_ORDER_RESPONSE = 0.0
    # PARTIAL (HES-MATH-BEHAV-56): 39_SPEC (dom(x+ε)-2dom(x)+dom(x-ε))/(‖ε‖²+eps).
    DOMINANCE_CURVATURE = 0.0
    # PARTIAL (HES-MATH-BEHAV-56): 39_SPEC (ent(x+ε)-2ent(x)+ent(x-ε))/(‖ε‖²+eps).
    ENTROPY_CURVATURE = 0.0
    HIT_VECTOR_RANK = 1
    PRINCIPAL_COMPONENT_ENERGY_RATIO = 1.0
    CONDITION_NUMBER = 1.0
    SPECTRAL_GAP = 0.0

    # III. Depth growth from mass_at_depth (live where data exists)
    if len(mass_at_depth) >= 2 and mass_at_depth[0] > 0:
        DEPTH_GROWTH_RATIO = mass_at_depth[1] / (mass_at_depth[0] + eps_val)
    else:
        DEPTH_GROWTH_RATIO = 0.0
    if len(mass_at_depth) >= 3:
        FIBONACCI_DEVIATION_SCORE = abs(
            mass_at_depth[2] - (mass_at_depth[1] + mass_at_depth[0])
        )
    else:
        FIBONACCI_DEVIATION_SCORE = 0.0
    EXPONENTIAL_FIT_ERROR = 0.0
    POWER_LAW_FIT_ERROR = 0.0

    # IV. Newtonian / functional analogies — PARTIAL (HES-MATH-BEHAV-57); need E(x±ε) / E∘E.
    # 39_SPEC: POTENTIAL_GRADIENT = dominance(x+ε)-dominance(x)
    POTENTIAL_GRADIENT = 0.0
    # 39_SPEC: min ‖ε‖ that flips dominant family; no-flip → max tested (here identity 1.0)
    ESCAPE_ENERGY_THRESHOLD = 1.0
    # 39_SPEC: ‖∇dominance‖ finite-difference magnitude
    FORCE_ANALOG_MAGNITUDE = 0.0
    # 39_SPEC: monotonicity over perturbation sample (vacuous True without sample)
    MONOTONICITY_CHECK = True
    # 39_SPEC: E(E(x))≈E(x); vacuous True without re-entrant E
    FIXED_POINT_DETECTION = True
    # 39_SPEC: E³(x)≈x period-3; vacuous False without re-entrant E
    CYCLE_DETECTION_FUNCTIONAL = False

    LYAPUNOV_ESTIMATE = 0.0
    if perturbation_enabled and isinstance(perturbation_series, dict):
        epsilon_magnitude = _numeric(perturbation_series, "epsilon_magnitude")
        plus = perturbation_series.get("plus")
        minus = perturbation_series.get("minus")
        plus = plus if isinstance(plus, dict) else {}
        minus = minus if isinstance(minus, dict) else {}
        plus_l1 = _snapshot_l1(plus)
        minus_l1 = _snapshot_l1(minus)

        if epsilon_magnitude is not None and epsilon_magnitude > 0.0:
            first_denominator = epsilon_magnitude + eps_val
            second_denominator = epsilon_magnitude**2 + eps_val
            base_output = _vector(perturbation_series.get("base_output"))
            plus_output = _vector(plus.get("output"))
            minus_output = _vector(minus.get("output"))

            if _same_length_vectors(base_output, plus_output):
                output_delta_norm = _difference_norm(plus_output, base_output)
                INPUT_PERTURBATION_RESPONSE = output_delta_norm / first_denominator
                LYAPUNOV_ESTIMATE = math.log(
                    (output_delta_norm + eps_val) / first_denominator
                )

            base_family = l1.get("DOMINANT_FAMILY_ID")
            plus_family = plus_l1.get("DOMINANT_FAMILY_ID")
            if base_family is not None and plus_family is not None:
                DOMINANT_FAMILY_STABILITY = base_family == plus_family

            base_coverage = _numeric(l1, "COVERAGE_RATIO")
            plus_coverage = _numeric(plus_l1, "COVERAGE_RATIO")
            if base_coverage is not None and plus_coverage is not None:
                COVERAGE_GRADIENT = (
                    plus_coverage - base_coverage
                ) / first_denominator

            base_entropy = _numeric(l1, "FAMILY_ENTROPY")
            plus_entropy = _numeric(plus_l1, "FAMILY_ENTROPY")
            if base_entropy is not None and plus_entropy is not None:
                ENTROPY_GRADIENT = (
                    plus_entropy - base_entropy
                ) / first_denominator

            base_dominance = _numeric(l1, "DOMINANCE_RATIO")
            plus_dominance = _numeric(plus_l1, "DOMINANCE_RATIO")
            if base_dominance is not None and plus_dominance is not None:
                POTENTIAL_GRADIENT = plus_dominance - base_dominance
                FORCE_ANALOG_MAGNITUDE = abs(
                    POTENTIAL_GRADIENT / first_denominator
                )

            if _same_length_vectors(base_output, plus_output, minus_output):
                second_difference = [
                    plus_value - 2.0 * base_value + minus_value
                    for plus_value, base_value, minus_value in zip(
                        plus_output, base_output, minus_output
                    )
                ]
                SECOND_ORDER_RESPONSE = (
                    math.sqrt(sum(value**2 for value in second_difference))
                    / second_denominator
                )

            minus_dominance = _numeric(minus_l1, "DOMINANCE_RATIO")
            if (
                base_dominance is not None
                and plus_dominance is not None
                and minus_dominance is not None
            ):
                DOMINANCE_CURVATURE = (
                    plus_dominance
                    - 2.0 * base_dominance
                    + minus_dominance
                ) / second_denominator

            minus_entropy = _numeric(minus_l1, "FAMILY_ENTROPY")
            if (
                base_entropy is not None
                and plus_entropy is not None
                and minus_entropy is not None
            ):
                ENTROPY_CURVATURE = (
                    plus_entropy - 2.0 * base_entropy + minus_entropy
                ) / second_denominator

            points = _perturbation_points(l1, perturbation_series, epsilon_magnitude)
            if base_family is not None:
                classified_points = [
                    (magnitude, point_l1.get("DOMINANT_FAMILY_ID"))
                    for magnitude, point_l1, _ in points
                    if point_l1.get("DOMINANT_FAMILY_ID") is not None
                ]
                if classified_points:
                    stable_magnitudes = [
                        magnitude
                        for magnitude, family in classified_points
                        if family == base_family
                    ]
                    flip_magnitudes = [
                        magnitude
                        for magnitude, family in classified_points
                        if family != base_family
                    ]
                    STABILITY_RADIUS = max(stable_magnitudes, default=0.0)
                    ESCAPE_ENERGY_THRESHOLD = (
                        min(flip_magnitudes)
                        if flip_magnitudes
                        else max(magnitude for magnitude, _ in classified_points)
                    )

            monotonic_points = []
            for _, point_l1, intensity in points:
                dominance = _numeric(point_l1, "DOMINANCE_RATIO")
                if intensity is not None and dominance is not None:
                    monotonic_points.append((intensity, dominance))
            if len(monotonic_points) >= 2:
                ordered_dominance = [
                    dominance for _, dominance in sorted(monotonic_points)
                ]
                nondecreasing = all(
                    left <= right
                    for left, right in zip(
                        ordered_dominance, ordered_dominance[1:]
                    )
                )
                nonincreasing = all(
                    left >= right
                    for left, right in zip(
                        ordered_dominance, ordered_dominance[1:]
                    )
                )
                MONOTONICITY_CHECK = nondecreasing or nonincreasing

            iterate_2_output = _vector(
                perturbation_series.get("iterate_2_output")
            )
            if _same_length_vectors(base_output, iterate_2_output):
                FIXED_POINT_DETECTION = _vectors_close(
                    iterate_2_output, base_output, eps_val
                )

            input_vector = _vector(perturbation_series.get("input_vector"))
            iterate_3_output = _vector(
                perturbation_series.get("iterate_3_output")
            )
            if _same_length_vectors(input_vector, iterate_3_output):
                CYCLE_DETECTION_FUNCTIONAL = _vectors_close(
                    iterate_3_output, input_vector, eps_val
                )

    GLOBAL_STABILITY_SCORE = 1.0 / (1.0 + CONDITION_NUMBER + abs(LYAPUNOV_ESTIMATE))
    CONCEPTUAL_COHERENCE_INDEX = STABILITY_RADIUS * (1.0 - norm_entropy) * GLOBAL_STABILITY_SCORE

    return {
        "INPUT_PERTURBATION_RESPONSE": INPUT_PERTURBATION_RESPONSE,
        "DOMINANT_FAMILY_STABILITY": DOMINANT_FAMILY_STABILITY,
        "COVERAGE_GRADIENT": COVERAGE_GRADIENT,
        "ENTROPY_GRADIENT": ENTROPY_GRADIENT,
        "STABILITY_RADIUS": STABILITY_RADIUS,
        "SECOND_ORDER_RESPONSE": SECOND_ORDER_RESPONSE,
        "DOMINANCE_CURVATURE": DOMINANCE_CURVATURE,
        "ENTROPY_CURVATURE": ENTROPY_CURVATURE,
        "HIT_VECTOR_RANK": HIT_VECTOR_RANK,
        "PRINCIPAL_COMPONENT_ENERGY_RATIO": PRINCIPAL_COMPONENT_ENERGY_RATIO,
        "CONDITION_NUMBER": CONDITION_NUMBER,
        "SPECTRAL_GAP": SPECTRAL_GAP,
        "DEPTH_GROWTH_RATIO": DEPTH_GROWTH_RATIO,
        "FIBONACCI_DEVIATION_SCORE": FIBONACCI_DEVIATION_SCORE,
        "EXPONENTIAL_FIT_ERROR": EXPONENTIAL_FIT_ERROR,
        "POWER_LAW_FIT_ERROR": POWER_LAW_FIT_ERROR,
        "POTENTIAL_GRADIENT": POTENTIAL_GRADIENT,
        "ESCAPE_ENERGY_THRESHOLD": ESCAPE_ENERGY_THRESHOLD,
        "FORCE_ANALOG_MAGNITUDE": FORCE_ANALOG_MAGNITUDE,
        "MONOTONICITY_CHECK": MONOTONICITY_CHECK,
        "FIXED_POINT_DETECTION": FIXED_POINT_DETECTION,
        "CYCLE_DETECTION_FUNCTIONAL": CYCLE_DETECTION_FUNCTIONAL,
        "LYAPUNOV_ESTIMATE": LYAPUNOV_ESTIMATE,
        "GLOBAL_STABILITY_SCORE": GLOBAL_STABILITY_SCORE,
        "CONCEPTUAL_COHERENCE_INDEX": CONCEPTUAL_COHERENCE_INDEX,
    }


def run(input: LayerInput) -> LayerOutput:
    """Layer-6 public entry point. Consumes LayerInput, returns LayerOutput. No other public entry points."""
    t0 = time.perf_counter()
    meta = input.metadata
    layers = meta.get("layers", {})
    l1 = layers.get(1)
    l2 = layers.get(2)
    if not l1 or not l2:
        raise ValueError("Layer 6 requires layer 1 and 2 results in input.metadata['layers']")
    F = int(meta.get("F", 288))
    result = compute_L6(
        l1,
        l2,
        F=F,
        perturbation_enabled=bool(meta.get("l6_perturbation_enabled", False)),
        perturbation_series=meta.get("l6_perturbation_series"),
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return LayerOutput(
        layer_id=6,
        result=result,
        diagnostics={"layer_id": 6, "execution_time_ms": round(elapsed_ms, 6)},
    )
