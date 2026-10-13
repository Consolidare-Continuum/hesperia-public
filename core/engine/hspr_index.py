# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Multiscale system HSPR — **Engine Dynamics v0.5** KPI (sealed_multiscale_stack, E2E 10c).

NOT the same as calibration.hspr_field (family-field Σ̂/Ê six-observable HSPR on F).
Spec: spec/hspr_calibration_index.md — naming overlap is historical; refactor may rename.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

__all__ = ["HSPRSystemWeights", "compute_hspr_index", "field_state_from_hex_stack"]


@dataclass(frozen=True)
class HSPRSystemWeights:
    a1: float = 0.28
    a2: float = 0.24
    a3: float = 0.26
    a4: float = 0.22


def _hat(x: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    return float(np.clip(x / (x + scale), 0.0, 1.0))


def compute_hspr_index(
    field_state: Mapping[str, Any],
    *,
    weights: HSPRSystemWeights | None = None,
    scales: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """
    HSPR_sys = ã1 Ê_act + ã2 v̂ + ã3 P̂ + ã4 D̂ with affine map to [0,1].

    field_state keys:
    - activation_energy: Σ A_h²
    - propagation_strength
    - contradiction_pressure
    - narrative_density
    """
    w = weights or HSPRSystemWeights()
    sc = dict(scales or {})
    e_act = float(field_state.get("activation_energy", 0.0))
    v = float(field_state.get("propagation_strength", 0.0))
    p = float(field_state.get("contradiction_pressure", 0.0))
    d = float(field_state.get("narrative_density", 0.0))

    e_hat = _hat(e_act, float(sc.get("activation_energy", 500.0)))
    v_hat = _hat(v, float(sc.get("propagation_strength", 0.05)))
    p_hat = _hat(p, float(sc.get("contradiction_pressure", 5.0)))
    d_hat = _hat(d, float(sc.get("narrative_density", 0.02)))

    raw = w.a1 * e_hat + w.a2 * v_hat + w.a3 * p_hat + w.a4 * d_hat
    denom = w.a1 + w.a2 + w.a3 + w.a4
    hspr = float(np.clip(raw / denom, 0.0, 1.0)) if denom > 0 else 0.0
    return {
        "hspr_index": hspr,
        "components_hat": {
            "activation_energy_hat": e_hat,
            "propagation_strength_hat": v_hat,
            "contradiction_pressure_hat": p_hat,
            "narrative_density_hat": d_hat,
        },
        "components_raw": {
            "activation_energy": e_act,
            "propagation_strength": v,
            "contradiction_pressure": p,
            "narrative_density": d,
        },
    }


def field_state_from_hex_stack(
    A_hex: np.ndarray,
    product_signals: Mapping[str, Any],
) -> dict[str, Any]:
    a = np.asarray(A_hex, dtype=np.float64)
    activation_energy = float(np.sum(a * a))
    return {
        "activation_energy": activation_energy,
        "propagation_strength": float(product_signals.get("propagation_strength", 0.0)),
        "contradiction_pressure": float(product_signals.get("contradiction_pressure", 0.0)),
        "narrative_density": float(product_signals.get("narrative_density", 0.0)),
    }
