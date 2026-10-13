# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Macro–micro consistency: family activation vs hex aggregate."""

from __future__ import annotations

from typing import Mapping

import numpy as np

__all__ = ["compute_family_multiscale_consistency"]


def compute_family_multiscale_consistency(
    hex_activation: np.ndarray,
    family_hex_map: Mapping[int, list[int] | tuple[int, ...]],
    family_activation: Mapping[int, float] | np.ndarray,
    *,
    eps: float = 1e-12,
) -> dict[int, float]:
    """
    Consistency(f) = 1 − |F_macro(f) − Σ_{h∈f} A_h| / max(|F_macro(f)|, ε)

    Clipped to [0, 1]. If macro mass is ~0, score 1 iff micro ~0 else 0.
    """
    a = np.asarray(hex_activation, dtype=np.float64).reshape(-1)

    def macro_val(f: int) -> float:
        if isinstance(family_activation, np.ndarray):
            return float(family_activation[f]) if 0 <= f < len(family_activation) else 0.0
        return float(family_activation.get(f, 0.0))

    scores: dict[int, float] = {}
    for f, hexes in family_hex_map.items():
        fi = int(f)
        micro = float(sum(a[h] for h in hexes if 0 <= h < len(a)))
        macro = macro_val(fi)
        den = max(abs(macro), eps)
        if abs(macro) < eps:
            scores[fi] = 1.0 if abs(micro) < eps else 0.0
        else:
            scores[fi] = float(np.clip(1.0 - abs(macro - micro) / den, 0.0, 1.0))
    return scores
