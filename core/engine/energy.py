# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Centralized energy functionals for governed dynamics.

**Family field (1D):** matches ``extensions.dynamics.equations`` linearized energy:

    E(F) = (α/2) Fᵀ L F + (β/2) Fᵀ R F + (γ/2) Fᵀ C F − δ Sᵀ F

**Hex field (2D):** task-aligned functional (ring Laplacian per family + contradiction on aggregates):

    E(H) = Σ_m h_mᵀ L h_m + λ Sᵀ C_F S − Σ_m S_H[m]ᵀ h_m,   S_m = Σ_k H[m,k]

``λ`` (``lam_contra``) weights the contradiction term relative to the Laplacian quadratic form.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

__all__ = [
    "EnergyMode",
    "EnergyControlParams",
    "compute_energy_family_1d",
    "compute_energy_hex_2d",
    "clip_fraction_01",
    "apply_clip_01_with_stats",
]


class EnergyMode(str, Enum):
    """``strict``: energy must not increase (beyond float noise). ``soft``: allow small ascent."""

    strict = "strict"
    soft = "soft"


@dataclass(frozen=True)
class EnergyControlParams:
    """Energy-gated stepping + adaptive dt (family Euler) / line search (hex)."""

    mode: EnergyMode = EnergyMode.strict
    # Soft mode: allow E_next <= E_prev + epsilon_energy_soft
    epsilon_energy_soft: float = 1e-5
    # Adaptive dt (family field)
    dt_decay: float = 0.5
    dt_growth: float = 1.1
    dt_min: float = 1e-12
    dt_max: float = 10.0
    stable_steps_for_growth: int = 4
    max_dt_halving_retries: int = 28
    # Convergence (combined with field-specific ε in callers)
    epsilon_delta_a: float = 1e-9
    epsilon_delta_e: float = 1e-10
    # Clipping is safeguard only — report fraction of entries that hit bounds
    clip_warn_threshold: float = 0.15
    clip_fail_threshold: float = 0.85
    # Line search (hex local / discrete): η multipliers
    line_search_factors: tuple[float, ...] = (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125)
    # Float tolerance for strict monotone check
    energy_tol_strict: float = 1e-12


def compute_energy_family_1d(
    F: np.ndarray | Any,
    S: np.ndarray | Any,
    L: np.ndarray | Any,
    R: np.ndarray | Any,
    C: np.ndarray | Any,
    *,
    alpha: float,
    beta: float,
    gamma: float,
    delta: float,
) -> float:
    """
    Canonical linearized family energy (same formula as ``equations.compute_energy``).
    """
    f = np.asarray(F, dtype=np.float64).reshape(-1)
    s = np.asarray(S, dtype=np.float64).reshape(-1)
    l = np.asarray(L, dtype=np.float64)
    r = np.asarray(R, dtype=np.float64)
    c = np.asarray(C, dtype=np.float64)
    n = f.shape[0]
    if s.shape[0] != n or l.shape != (n, n) or r.shape != (n, n) or c.shape != (n, n):
        raise ValueError("compute_energy_family_1d: shape mismatch")
    return float(
        0.5 * alpha * float(f.T @ l @ f)
        + 0.5 * beta * float(f.T @ r @ f)
        + 0.5 * gamma * float(f.T @ c @ f)
        - delta * float(s.T @ f)
    )


def compute_energy_hex_2d(
    H: np.ndarray | Any,
    L_ring: np.ndarray | Any,
    C_F: np.ndarray | Any,
    S_H: np.ndarray | Any,
    *,
    lam_contra: float = 1.0,
) -> float:
    """
    Hex energy: smooth (per-family ring Laplacian quadratic) + λ·SᵀC S − ⟨S_H, H⟩.
    """
    h = np.asarray(H, dtype=np.float64)
    if h.ndim != 2:
        raise ValueError("H must be 2D (n_families, n_hex_per_family)")
    nf, nh = h.shape
    l_ring = np.asarray(L_ring, dtype=np.float64)
    c_f = np.asarray(C_F, dtype=np.float64)
    s_h = np.asarray(S_H, dtype=np.float64)
    if l_ring.shape != (nh, nh):
        raise ValueError("L_ring shape mismatch")
    if c_f.shape != (nf, nf):
        raise ValueError("C_F shape mismatch")
    if s_h.shape != h.shape:
        raise ValueError("S_H must match H shape")

    e_smooth = 0.0
    for m in range(nf):
        hm = h[m]
        e_smooth += float(hm @ (l_ring @ hm))
    s = h.sum(axis=1)
    e_contra = float(s @ (c_f @ s))
    e_source = float(np.sum(s_h * h))
    return float(e_smooth + lam_contra * e_contra - e_source)


def clip_fraction_01(x: np.ndarray, *, lo: float = 0.0, hi: float = 1.0) -> float:
    """Fraction of entries already at or beyond bounds before clip (safeguard metric)."""
    a = np.asarray(x, dtype=np.float64)
    at_lo = np.sum(a <= lo + 1e-15)
    at_hi = np.sum(a >= hi - 1e-15)
    return float((at_lo + at_hi) / max(1, a.size))


def apply_clip_01_with_stats(
    x: np.ndarray,
    *,
    clip: bool,
    lo: float = 0.0,
    hi: float = 1.0,
) -> tuple[np.ndarray, float]:
    """
    If ``clip``, clip to ``[lo, hi]`` and return (clipped_array, fraction_of_elements_changed).
    """
    a = np.asarray(x, dtype=np.float64).copy()
    if not clip:
        return a, 0.0
    before = a.copy()
    np.clip(a, lo, hi, out=a)
    changed = np.sum(~np.isclose(before, a, rtol=0.0, atol=0.0))
    return a, float(changed / max(1, a.size))


def energy_acceptable(
    e_prev: float,
    e_next: float,
    ec: EnergyControlParams,
) -> bool:
    if ec.mode == EnergyMode.soft:
        return e_next <= e_prev + ec.epsilon_energy_soft
    return e_next <= e_prev + ec.energy_tol_strict
