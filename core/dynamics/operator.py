"""Canonical dynamics operator for hex-state updates."""

from __future__ import annotations

from core.dynamics.constants import get_constant
from core.dynamics.numeric import EPS, clamp_non_negative, quantize


def compute_h_total(
    state: dict[str, float], params: dict[str, float]
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Canonical update law.

    H_total = H_self + H_coupling - H_inhibition
    """
    if not state:
        return {}, {
            "total_energy_before": 0.0,
            "total_energy_after": 0.0,
            "expected_decay_loss": 0.0,
            "actual_loss": 0.0,
            "forbidden_loss": 0.0,
            "energy_conservation_ok": True,
        }
    decay = max(0.0, min(1.0, float(params.get("decay", get_constant("operator.decay_default", 0.05)))))
    coupling_alpha = max(
        0.0,
        min(1.0, float(params.get("coupling_alpha", get_constant("operator.coupling_alpha_default", 0.12)))),
    )
    inhibition_alpha = max(
        0.0,
        min(1.0, float(params.get("inhibition_alpha", get_constant("operator.inhibition_alpha_default", 0.1)))),
    )
    total = sum(max(0.0, float(v)) for v in state.values())
    mean = total / max(1, len(state))

    out: dict[str, float] = {}
    for key, value in state.items():
        v = clamp_non_negative(float(value))
        h_self = v * (1.0 - decay)
        h_coupling = coupling_alpha * mean
        h_inhibition = inhibition_alpha * v
        out[key] = clamp_non_negative(h_self + h_coupling - h_inhibition)

    total_before = quantize(sum(max(0.0, float(v)) for v in state.values()))
    total_after = quantize(sum(out.values()))
    expected_loss = quantize(decay * total_before)
    actual_loss = quantize(max(0.0, total_before - total_after))
    tolerance = float(get_constant("operator.energy_conservation_tolerance", 1e-6))
    forbidden_loss = max(0.0, actual_loss - expected_loss)
    energy_ok = forbidden_loss <= max(tolerance, EPS)
    diagnostics = {
        "total_energy_before": total_before,
        "total_energy_after": total_after,
        "expected_decay_loss": expected_loss,
        "actual_loss": actual_loss,
        "forbidden_loss": quantize(forbidden_loss),
        "energy_conservation_ok": bool(energy_ok),
    }
    return out, diagnostics

