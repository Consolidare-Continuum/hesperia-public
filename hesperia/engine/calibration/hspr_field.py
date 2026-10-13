# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
HSPR index: single global structural scalar from normalized observables.

Spec: spec/semantic_field_canon.md §8
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from core.engine.observables import FieldObservables


@dataclass(frozen=True)
class HSPRWeights:
    """w1..w6 for Σ̂, Q̂, Ê, K̂, R̂, D̂ (positive weights only)."""

    w_sigma: float = 0.20
    w_Q: float = 0.20
    w_E: float = 0.20
    w_K: float = 0.15
    w_R: float = 0.15
    w_D: float = 0.10

    def sum_pos(self) -> float:
        return self.w_sigma + self.w_Q + self.w_E

    def sum_neg(self) -> float:
        return self.w_K + self.w_R + self.w_D

    def total(self) -> float:
        return self.sum_pos() + self.sum_neg()


@dataclass(frozen=True)
class ObservableScales:
    """Characteristic scales for x̂ = x / (x + scale) (x ≥ 0)."""

    E: float = 5.0
    K: float = 2.0
    R: float = 5.0
    D: float = 3.0
    Q: float = 8.0


def _hat_positive(x: float, scale: float) -> float:
    if scale <= 0:
        raise ValueError("scale must be > 0")
    if x < 0:
        x = 0.0
    return float(x / (x + scale))


def _hat_sigma(sigma_l2: float) -> float:
    """Map step norm to [0,1]: small step → high (coherent / settled)."""
    return float(1.0 / (1.0 + max(0.0, sigma_l2)))


def normalize_observables(
    obs: FieldObservables,
    scales: ObservableScales | None = None,
) -> dict[str, float]:
    """
    Ê, K̂, R̂, D̂, Q̂ via x/(x+scale); Σ̂ = 1/(1+Σ).
    All values in [0,1] for non-negative raw observables; Σ̂ in (0,1].
    """
    s = scales or ObservableScales()
    return {
        "E_hat": _hat_positive(obs.E, s.E),
        "K_hat": _hat_positive(obs.K, s.K),
        "R_hat": _hat_positive(obs.R, s.R),
        "D_hat": _hat_positive(obs.D, s.D),
        "Q_hat": _hat_positive(obs.Q, s.Q),
        "Sigma_hat": _hat_sigma(obs.Sigma),
    }


def compute_hspr(
    hats: dict[str, float],
    weights: HSPRWeights | None = None,
) -> float:
    """
    HSPR = w1 Σ̂ + w2 Q̂ + w3 Ê - w4 K̂ - w5 R̂ - w6 D̂, affine-mapped to [0,1].

    hats must include keys: Sigma_hat, Q_hat, E_hat, K_hat, R_hat, D_hat.
    """
    w = weights or HSPRWeights()
    sh = hats["Sigma_hat"]
    qh = hats["Q_hat"]
    eh = hats["E_hat"]
    kh = hats["K_hat"]
    rh = hats["R_hat"]
    dh = hats["D_hat"]
    raw = (
        w.w_sigma * sh
        + w.w_Q * qh
        + w.w_E * eh
        - w.w_K * kh
        - w.w_R * rh
        - w.w_D * dh
    )
    denom = w.total()
    if denom <= 0:
        raise ValueError("weights must sum to positive total")
    hspr = (raw + w.sum_neg()) / denom
    return float(np.clip(hspr, 0.0, 1.0))


def hspr_from_observables(
    obs: FieldObservables,
    *,
    scales: ObservableScales | None = None,
    weights: HSPRWeights | None = None,
) -> tuple[float, dict[str, float]]:
    """Normalize then HSPR; returns (hspr, hats)."""
    hats = normalize_observables(obs, scales)
    return compute_hspr(hats, weights), hats


def interpret_hspr(hspr: float) -> str:
    """Product bands from semantic_field_canon.md."""
    if hspr >= 0.8:
        return "coherent_narrative"
    if hspr >= 0.5:
        return "moderate_tension"
    if hspr >= 0.2:
        return "unstable_narrative"
    return "contradiction_dominated"


def hspr_payload(obs: FieldObservables, **kwargs: Any) -> dict[str, Any]:
    """JSON-friendly bundle for dossiers / API."""
    hspr, hats = hspr_from_observables(obs, **kwargs)
    return {
        "hspr": round(hspr, 6),
        "hspr_band": interpret_hspr(hspr),
        "observables": obs.as_dict(),
        "observables_normalized": {k: round(v, 6) for k, v in hats.items()},
    }


__all__ = [
    "HSPRWeights",
    "ObservableScales",
    "normalize_observables",
    "compute_hspr",
    "hspr_from_observables",
    "interpret_hspr",
    "hspr_payload",
]
