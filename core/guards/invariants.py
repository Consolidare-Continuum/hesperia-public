"""Hard invariant enforcement for execution flow state."""

from __future__ import annotations

from typing import Any

from core.dynamics.numeric import EPS, clamp_non_negative, clamp01, quantize
from core.state.semantic_state import SemanticState


def enforce_invariants(
    state: SemanticState,
    *,
    max_total_mass: float = 1e6,
    clamp: bool = True,
) -> tuple[SemanticState, list[str]]:
    violations: list[str] = []
    mass = {k: float(v) for k, v in state.mass_vector.items()}
    activation = {k: float(v) for k, v in state.activation_vector.items()}

    for bucket_name, bucket in (("mass", mass), ("activation", activation)):
        for key, value in list(bucket.items()):
            if value < 0:
                violations.append(f"negative_{bucket_name}:{key}")
                if clamp:
                    bucket[key] = 0.0
            elif clamp:
                bucket[key] = clamp_non_negative(value) if bucket_name == "mass" else clamp01(value)

    total_mass = sum(mass.values())
    if total_mass > max_total_mass + EPS:
        violations.append("total_mass_bound_exceeded")
        if clamp and total_mass > 0:
            scale = max_total_mass / total_mass
            mass = {k: v * scale for k, v in mass.items()}

    act_total = sum(activation.values())
    if act_total > EPS:
        activation = {k: clamp01(v / act_total) for k, v in activation.items()}
    else:
        violations.append("activation_zero_sum")
        activation = {k: 0.0 for k in activation}

    mass = {k: quantize(v) for k, v in mass.items()}
    activation = {k: quantize(v) for k, v in activation.items()}

    new_state = SemanticState(
        energy_vector=dict(state.energy_vector),
        activation_vector=activation,
        mass_vector=mass,
        position=dict(state.position),
    )
    return new_state, violations


def log_invariant_violations(violations: list[str], sink: dict[str, Any]) -> None:
    if not violations:
        return
    sink.setdefault("invariant_violations", [])
    sink["invariant_violations"].extend(violations)

