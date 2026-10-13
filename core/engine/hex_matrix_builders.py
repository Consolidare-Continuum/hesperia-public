# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Deterministic builders for hex microphysics (ring Laplacian, resistance, P_CH-style sources).

Spec: spec/hex_microphysics_canon.md
Geometry: core.topology.invariant_catalog
"""

from __future__ import annotations

import os
from typing import Sequence

import numpy as np
from scipy.sparse import issparse

from core.topology.invariant_catalog import (
    FAMILIES_PER_AREA,
    HEXES_PER_FAMILY,
    TOTAL_FAMILIES,
    TOTAL_HEXES,
)

__all__ = [
    "NUM_FAMILIES_HEX",
    "HEXES_PER_FAMILY_CANON",
    "TOTAL_HEXES_CANON",
    "hex_linear_index",
    "family_and_local_from_linear",
    "build_ring_laplacian",
    "build_uniform_hex_resistance",
    "apply_pch_to_concept_activation",
    "family_source_to_hex_uniform",
    "concept_family_weights_to_hex_source",
]


NUM_FAMILIES_HEX = TOTAL_FAMILIES
HEXES_PER_FAMILY_CANON = HEXES_PER_FAMILY
TOTAL_HEXES_CANON = TOTAL_HEXES


def hex_linear_index(family_id: int, hex_within_family: int) -> int:
    """Global linear hex index u ∈ [0, Nh)."""
    if not (0 <= family_id < NUM_FAMILIES_HEX) or not (0 <= hex_within_family < HEXES_PER_FAMILY_CANON):
        raise ValueError("family_id or hex_within_family out of range")
    return int(family_id * HEXES_PER_FAMILY_CANON + hex_within_family)


def family_and_local_from_linear(u: int) -> tuple[int, int]:
    """Inverse map: u → (family m, local hex index)."""
    if not (0 <= u < TOTAL_HEXES_CANON):
        raise ValueError(f"hex index u={u} out of [0, {TOTAL_HEXES_CANON})")
    m = u // HEXES_PER_FAMILY_CANON
    j = u % HEXES_PER_FAMILY_CANON
    return m, j


def build_ring_laplacian(n_hex: int) -> np.ndarray:
    """
    Unweighted cycle graph Laplacian L = D - W, W_ij = 1 on ring neighbors.
    Used per family block when W_H is intra-family ring (canon §5).
    """
    if n_hex < 2:
        raise ValueError("n_hex must be >= 2 for ring")
    w = np.zeros((n_hex, n_hex), dtype=np.float64)
    for i in range(n_hex):
        w[i, (i - 1) % n_hex] = 1.0
        w[i, (i + 1) % n_hex] = 1.0
    d = np.diag(w.sum(axis=1))
    return d - w


_UNIFORM_INJECTION_ENV = "HESPERIA_PCH_UNIFORM_INJECTION_DEV"


def _uniform_injection_dev_only() -> bool:
    return os.environ.get(_UNIFORM_INJECTION_ENV) == "1"


def apply_pch_to_concept_activation(
    a_concept: np.ndarray | Sequence[float],
    pch,
    *,
    n_families: int | None = None,
    n_hex_per_family: int | None = None,
) -> np.ndarray:
    """
    **Production path:** ``A_hex.flat = P_CH @ a_concept`` then reshape ``(n_families, n_hex_per_family)``.

    ``a_concept`` length must match ``P_CH.shape[1]`` (pad/truncate internally to ``n_concepts``).
    """
    if not issparse(pch):
        raise TypeError("pch must be a scipy.sparse sparse matrix")
    a = np.maximum(0.0, np.asarray(a_concept, dtype=np.float64).reshape(-1))
    n_c = int(pch.shape[1])
    n_hex_tot = int(pch.shape[0])
    if a.size < n_c:
        a = np.pad(a, (0, n_c - int(a.size)))
    elif a.size > n_c:
        a = a[:n_c].copy()
    flat = pch @ a
    nf = int(n_families) if n_families is not None else NUM_FAMILIES_HEX
    nh = int(n_hex_per_family) if n_hex_per_family is not None else (n_hex_tot // nf)
    if nf * nh != flat.size:
        raise ValueError(
            f"P_CH @ a_concept length {flat.size} does not match n_families*n_hex = {nf}*{nh}"
        )
    return np.asarray(flat).reshape(nf, nh)


def build_uniform_hex_resistance(
    n_families: int,
    n_hex_per_family: int,
    r: float,
) -> np.ndarray:
    """R_H diagonal values r_u ≡ r as (n_families, n_hex_per_family)."""
    if r < 0:
        raise ValueError("r must be non-negative")
    return np.full((n_families, n_hex_per_family), float(r), dtype=np.float64)


def family_source_to_hex_uniform(s_family: np.ndarray | Sequence[float]) -> np.ndarray:
    """
    **DEV / tests only:** uniform spread. Production must use ``apply_pch_to_concept_activation``.
    """
    if not _uniform_injection_dev_only():
        raise RuntimeError(
            "Uniform hex injection is forbidden in production. "
            "Use apply_pch_to_concept_activation(..., load_pch()). "
            f"Set {_UNIFORM_INJECTION_ENV}=1 for legacy unit tests."
        )
    sf = np.asarray(s_family, dtype=np.float64).reshape(-1)
    n = sf.shape[0]
    out = np.zeros((n, HEXES_PER_FAMILY_CANON), dtype=np.float64)
    denom = float(HEXES_PER_FAMILY_CANON)
    for m in range(min(n, out.shape[0])):
        out[m, :] = sf[m] / denom
    return out


def concept_family_weights_to_hex_source(
    weights_by_family: np.ndarray | Sequence[float],
    *,
    n_hex_per_family: int | None = None,
) -> np.ndarray:
    """
    **DEPRECATED / DEV-only:** uniform ``1/n_hex`` per family row.

    Production uses ``apply_pch_to_concept_activation`` with governed ``P_CH``.
    """
    if not _uniform_injection_dev_only():
        raise RuntimeError(
            "concept_family_weights_to_hex_source (uniform injection) is forbidden in production. "
            "Use core.engine.pch_loader.load_pch and apply_pch_to_concept_activation. "
            f"Set {_UNIFORM_INJECTION_ENV}=1 for legacy unit tests."
        )
    nh = n_hex_per_family or HEXES_PER_FAMILY_CANON
    wf = np.maximum(0.0, np.asarray(weights_by_family, dtype=np.float64).reshape(-1))
    n_f = wf.shape[0]
    out = np.zeros((n_f, nh), dtype=np.float64)
    for m in range(n_f):
        out[m, :] = wf[m] / float(nh)
    return out
