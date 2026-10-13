# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Canonical hex → family aggregation: F_j = Σ_h w_hj A_h.

Engine Dynamics v0.5: default singleton columns; JSON overrides sparse only (no full 72k×288 matrix shipped).
Swampy: hex_id string format (A3_F12_H05) must stay aligned with invariant_catalog layout.
Spec: spec/hex_family_bridge.md · assets/topology/hex_family_weights.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np

_HEX_ID_RE = re.compile(
    r"^A(\d+)_F(\d+)_H(\d+)$",
    re.I,
)

__all__ = [
    "parse_hex_id_to_linear_index",
    "load_hex_family_overrides",
    "default_hex_family_weight_matrix_2d",
    "compute_family_activation",
]


def parse_hex_id_to_linear_index(
    hex_id: str,
    *,
    hexes_per_family: int = 250,
    families_per_area: int = 24,
) -> int:
    """
    A{area}_F{family_in_area}_H{hex_in_family} — all 1-based in spec convention.
    """
    m = _HEX_ID_RE.match(hex_id.strip().replace(" ", ""))
    if not m:
        raise ValueError(f"invalid hex_id: {hex_id!r}")
    area_1, f_area_1, h_fam_1 = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if area_1 < 1 or f_area_1 < 1 or h_fam_1 < 1:
        raise ValueError(hex_id)
    area_0 = area_1 - 1
    f_local_0 = f_area_1 - 1
    h_0 = h_fam_1 - 1
    global_fam = area_0 * families_per_area + f_local_0
    return int(global_fam * hexes_per_family + h_0)


def load_hex_family_overrides(
    path: Path | str | None = None,
) -> dict[int, dict[int, float]]:
    """
    Returns map linear_hex_index -> {family_global: weight, ...} normalized to sum 1.
    """
    root = Path(__file__).resolve().parents[2]
    p = Path(path) if path else root / "assets" / "topology" / "hex_family_weights.json"
    if not p.is_file():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    out: dict[int, dict[int, float]] = {}
    nh = int(raw.get("hexes_per_family", 250))
    fpa = 24
    for row in raw.get("exemplar_overrides") or []:
        hid = row.get("hex_id")
        fw = row.get("family_weights") or {}
        if not hid or not fw:
            continue
        u = parse_hex_id_to_linear_index(str(hid), hexes_per_family=nh, families_per_area=fpa)
        wmap = {int(k): float(v) for k, v in fw.items()}
        s = sum(wmap.values())
        if s <= 0:
            continue
        wmap = {j: v / s for j, v in wmap.items()}
        out[u] = wmap
    return out


def default_hex_family_weight_matrix_2d(
    n_families: int = 288,
    n_hex_per_family: int = 250,
) -> np.ndarray:
    """W[j, h_flat] with singleton columns (for documentation / tests)."""
    n = n_families * n_hex_per_family
    w = np.zeros((n_families, n), dtype=np.float64)
    for u in range(n):
        j = u // n_hex_per_family
        w[j, u] = 1.0
    return w


def compute_family_activation(
    A_hex: np.ndarray,
    weight_matrix: np.ndarray | None = None,
    *,
    n_families: int = 288,
    n_hex_per_family: int = 250,
    overrides: dict[int, dict[int, float]] | None = None,
) -> np.ndarray:
    """
    F_j = Σ_h w_hj A_h.

    If ``weight_matrix`` is (n_families, n_hex_flat), returns W @ A.

    Otherwise A_hex may be (n_families, n_hex_per_family) or flat length n_families*n_hex_per_family;
    default singleton aggregation with optional ``overrides`` (linear_index -> family weights).
    """
    if weight_matrix is not None:
        w = np.asarray(weight_matrix, dtype=np.float64)
        a = np.asarray(A_hex, dtype=np.float64).reshape(-1)
        if w.shape[1] != a.shape[0]:
            raise ValueError("weight_matrix columns must match len(A_hex)")
        return w @ a

    a = np.asarray(A_hex, dtype=np.float64)
    if a.ndim == 2:
        if a.shape != (n_families, n_hex_per_family):
            raise ValueError(f"A_hex 2D shape must be ({n_families},{n_hex_per_family})")
        flat = a.ravel(order="C")
    else:
        flat = a.reshape(-1)
        expected = n_families * n_hex_per_family
        if flat.shape[0] != expected:
            raise ValueError(f"flat A_hex length must be {expected}")

    ov = overrides if overrides is not None else {}
    f = np.zeros(n_families, dtype=np.float64)
    used: set[int] = set()
    for u, wmap in ov.items():
        if u < 0 or u >= flat.shape[0]:
            continue
        ah = float(flat[u])
        for j, wj in wmap.items():
            if 0 <= int(j) < n_families:
                f[int(j)] += wj * ah
        used.add(u)
    for u in range(flat.shape[0]):
        if u in used:
            continue
        j = u // n_hex_per_family
        f[j] += flat[u]
    return f


def repo_default_overrides() -> dict[int, dict[int, float]]:
    return load_hex_family_overrides()
