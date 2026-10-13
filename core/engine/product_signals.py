# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Canonical product signals — **Engine Dynamics v0.5** (hex-causal substrate).

All KPIs are derived from the hex field ``A_hex`` (families × hex-per-family). Family vector ``F``
and area vector are aggregations only — they must not be inputs to signal formulas.

Contradiction uses a **lifted** family coupling matrix ``C_F`` applied to Gram rows
``G_ij = A_hex[i,:]·A_hex[j,:]`` (equivalently a structured ``C_H`` quadratic form without building ``N×N``).

Ring adjacency ``L_H`` (within each family row) is the default neighbor model for hotspots.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

__all__ = [
    "compute_product_signals",
    "narrative_hotspot_mean_hex",
    "propagation_strength_hex",
    "narrative_density_hex",
    "contradiction_pressure_hex",
    "spatial_entropy_hex",
    "innovation_potential_hex",
    "hex_hotspot_ring_values",
    "try_triz_contradiction_pressure",
]


def _require_hex_tensor(A: np.ndarray, name: str = "A_hex") -> np.ndarray:
    a = np.asarray(A, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError(f"{name} must be 2-D (n_families × n_hexes), got shape {a.shape}")
    if a.size == 0 or a.shape[0] < 1 or a.shape[1] < 1:
        raise RuntimeError(f"{name} is empty — hex layer required for signal computation")
    return a


def narrative_hotspot_mean_hex(
    A_hex: np.ndarray,
    *,
    lam: float = 0.45,
) -> float:
    """
    Hotspot(h) = A_h + λ Σ_{nbr∈L_H} A_nbr with **ring** adjacency along each family row (periodic nh).
    Returns the mean over all hex cells.
    """
    a = _require_hex_tensor(A_hex, "A_hex")
    nf, nh = a.shape
    hot_sum = 0.0
    ncell = nf * nh
    for m in range(nf):
        row = a[m]
        for k in range(nh):
            nbr = row[(k - 1) % nh] + row[(k + 1) % nh]
            hot_sum += float(row[k] + lam * nbr)
    return hot_sum / max(ncell, 1)


def propagation_strength_hex(
    A_hex_t: np.ndarray,
    A_hex_t1: np.ndarray,
    *,
    dt: float = 1.0,
) -> float:
    """v = mean(|A_hex(t+1) − A_hex(t)|) / dt."""
    a0 = _require_hex_tensor(A_hex_t, "A_hex_t")
    a1 = _require_hex_tensor(A_hex_t1, "A_hex_t1")
    if a0.shape != a1.shape:
        raise ValueError("A_hex_t and A_hex_t1 must have the same shape")
    dA = np.abs(a1 - a0)
    return float(np.mean(dA) / max(dt, 1e-12))


def narrative_density_hex(A_hex: np.ndarray, *, active_theta: float = 1e-9) -> float:
    """density = sum(A_hex) / count(active hexes), active = {cells : A > θ}."""
    a = _require_hex_tensor(A_hex, "A_hex")
    flat = a.ravel()
    active = int(np.sum(flat > active_theta))
    return float(np.sum(flat) / max(active, 1))


def contradiction_pressure_hex(A_hex: np.ndarray, C_F: np.ndarray) -> float:
    """
    Quadratic form on hex state via family coupling lift (no F vector):

        P = Σ_{ij} C_F[i,j] * (A_hex[i,:] · A_hex[j,:])

    i.e. ``sum(C_F * (A_hex @ A_hex.T))`` elementwise then sum — uses only hex activations.
    """
    a = _require_hex_tensor(A_hex, "A_hex")
    c = np.asarray(C_F, dtype=np.float64)
    nf = a.shape[0]
    if c.shape != (nf, nf):
        raise ValueError(f"C_F must be ({nf},{nf}), got {c.shape}")
    gram = a @ a.T
    return float(np.sum(c * gram))


def spatial_entropy_hex(A_hex: np.ndarray) -> float:
    """Normalized Shannon entropy of the flattened hex mass distribution (0 = peaky, 1 ≈ uniform)."""
    a = _require_hex_tensor(A_hex, "A_hex")
    v = a.ravel()
    s = float(v.sum())
    n = v.size
    if s <= 1e-15:
        return 0.0
    p = v / s
    p = p[p > 1e-18]
    h = -float(np.sum(p * np.log(p)))
    return float(h / max(math.log(n), 1e-12))


def innovation_potential_hex(
    contradiction_pressure: float,
    A_hex: np.ndarray,
) -> float:
    """Innovation ∝ contradiction_density(A_hex) × spatial_entropy(A_hex); hex-only."""
    a = _require_hex_tensor(A_hex, "A_hex")
    mass = float(np.sum(a))
    contradiction_density = contradiction_pressure / max(mass * mass, 1e-12)
    se = spatial_entropy_hex(a)
    raw = contradiction_density * se
    return float(np.clip(raw, 0.0, 100.0))


def hex_hotspot_ring_values(
    A_hex: np.ndarray,
    *,
    lam: float = 0.45,
    cap: int = 96,
    max_families: int = 40,
    max_slots: int = 8,
) -> list[float]:
    """Deterministic hotspot samples (ring neighbors) for artifact / UI; hex-only."""
    a = _require_hex_tensor(A_hex, "A_hex")
    nf, nh = a.shape
    out: list[float] = []
    for m in range(min(nf, max_families)):
        row = a[m]
        for k in range(min(nh, max_slots)):
            nbr = row[(k - 1) % nh] + row[(k + 1) % nh]
            out.append(float(row[k] + lam * nbr))
            if len(out) >= cap:
                return out
    return out


def compute_product_signals(
    A_hex_before: np.ndarray,
    A_hex_after: np.ndarray,
    *,
    C_F: np.ndarray | None = None,
    lam: float = 0.45,
    active_theta: float = 1e-9,
    dt: float = 1.0,
) -> dict[str, Any]:
    """
    Compute all product signals from **hex fields only**.

    ``C_F`` (n_families × n_families) is used only inside ``contradiction_pressure_hex`` as a coupling
    lift on hex rows — not applied to a pre-aggregated family vector.

    Raises:
        RuntimeError: if either hex tensor is missing/empty.
    """
    a0 = _require_hex_tensor(A_hex_before, "A_hex_before")
    a1 = _require_hex_tensor(A_hex_after, "A_hex_after")
    if a0.shape != a1.shape:
        raise ValueError("A_hex_before and A_hex_after must have the same shape")

    hotspot_mean = narrative_hotspot_mean_hex(a0, lam=lam)
    propagation_strength = propagation_strength_hex(a0, a1, dt=dt)
    narrative_density = narrative_density_hex(a1, active_theta=active_theta)

    nf = a1.shape[0]
    c = np.asarray(C_F, dtype=np.float64) if C_F is not None else np.zeros((nf, nf))
    contradiction_pressure = contradiction_pressure_hex(a1, c)
    se = spatial_entropy_hex(a1)
    innovation_potential = innovation_potential_hex(contradiction_pressure, a1)

    return {
        "narrative_hotspot_mean": hotspot_mean,
        "contradiction_pressure": contradiction_pressure,
        "propagation_strength": propagation_strength,
        "narrative_density": narrative_density,
        "innovation_potential": innovation_potential,
        "spatial_entropy_hex": se,
        "novelty_index": se,
    }


def try_triz_contradiction_pressure(text: str) -> float | None:
    """Optional TRIZ-derived pressure (DEV / extension); does not substitute for hex-based P."""
    try:
        from hesperia.extensions.triz.pipeline import run_triz_analysis_complete

        r = run_triz_analysis_complete(text[:2000])
        d = r.get("contradiction_density") or r.get("commercial_intel", {}).get("contradiction_density")
        return float(d) if d is not None else None
    except Exception:
        return None
