# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Canonical Concept→Hex operator **P_CH** (v1).

Each concept column ``i`` (aligned with structural family channel ``i`` for v1) places mass only on
hex rows belonging to family ``i``, with **non-uniform** ring-shaped decay from a deterministic
per-concept center. Columns are **L1-normalized** to 1.

``A_hex`` (flattened) ``= P_CH @ A_concept`` with ``A_concept ∈ ℝ^{N_c}``, ``A_hex ∈ ℝ^{N_h}``.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix

__all__ = ["build_pch_v1", "expected_sparsity_ratio"]


def expected_sparsity_ratio(n_concepts: int, n_hex_per_family: int) -> float:
    """nnz / (n_hex_total * n_concepts) with full family-block support per column."""
    n_hex_total = n_concepts * n_hex_per_family
    nnz = n_concepts * n_hex_per_family
    return float(nnz) / float(max(1, n_hex_total * n_concepts))


def build_pch_v1(
    *,
    n_concepts: int = 288,
    n_hex_per_family: int = 250,
    decay: float = 0.12,
) -> csr_matrix:
    """
    Build sparse **P_CH** of shape ``(n_concepts * n_hex_per_family, n_concepts)``.

    For each concept ``i``, center index on the family ring:
    ``center_i = (37 * i + 13) mod n_hex_per_family`` (deterministic, disperses centers).

    Weight on local hex ``k`` (within family ``i``):
    ``w_k ∝ exp(-decay * d_ring(k, center_i))``, then column-normalized.
    """
    if n_concepts < 1 or n_hex_per_family < 2:
        raise ValueError("n_concepts >= 1 and n_hex_per_family >= 2 required")
    n_hex_total = n_concepts * n_hex_per_family
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []

    for i in range(n_concepts):
        center = (37 * i + 13) % n_hex_per_family
        wloc = np.zeros(n_hex_per_family, dtype=np.float64)
        for k in range(n_hex_per_family):
            d = abs(k - center)
            d = min(d, n_hex_per_family - d)
            wloc[k] = math.exp(-decay * float(d))
        s = float(wloc.sum())
        if s <= 0:
            raise RuntimeError("P_CH column normalization failed")
        wloc /= s
        base = i * n_hex_per_family
        for k in range(n_hex_per_family):
            val = float(wloc[k])
            if val > 1e-18:
                rows.append(base + k)
                cols.append(i)
                data.append(val)

    mat = csr_matrix((data, (rows, cols)), shape=(n_hex_total, n_concepts), dtype=np.float64)
    mat.eliminate_zeros()
    return mat


def pch_manifest_dict(mat: csr_matrix, *, n_hex_per_family: int, decay: float) -> dict[str, Any]:
    n_hex_total, n_concepts = mat.shape
    nnz = mat.nnz
    denom = max(1, n_hex_total * n_concepts)
    return {
        "version": "v1",
        "n_concepts": int(n_concepts),
        "n_hex": int(n_hex_total),
        "n_hex_per_family": int(n_hex_per_family),
        "decay": float(decay),
        "nnz": int(nnz),
        "sparsity": round(float(nnz) / float(denom), 8),
        "normalization": "column_l1",
        "file": "P_CH_v1.npz",
    }
