# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Single-step diffusion: convex combination of identity and matrix application.
Deterministic; pure numerical operations only. Used by sphere/propagation.
"""

from __future__ import annotations

import numpy as np


def diffuse_step(
    v: np.ndarray | list[float],
    W: np.ndarray,
    alpha: float,
) -> np.ndarray:
    """
    One diffusion step: (1 - alpha) * v + alpha * (v @ W).

    v: 1d array (length n).
    W: 2d array (n x n), typically row-stochastic.
    alpha: diffusion strength in [0, 1].

    Returns 1d float64 array of length n. Non-negative if v and W are non-negative.
    """
    v_arr = np.asarray(v, dtype=np.float64).flatten()
    W_arr = np.asarray(W, dtype=np.float64)
    if v_arr.ndim != 1 or W_arr.ndim != 2:
        raise ValueError("v must be 1d and W must be 2d")
    if v_arr.size != W_arr.shape[0] or W_arr.shape[0] != W_arr.shape[1]:
        raise ValueError("v length must match W shape (n x n)")
    if not (0 <= alpha <= 1):
        raise ValueError("alpha must be in [0, 1]")
    out = (1.0 - alpha) * v_arr + alpha * (v_arr @ W_arr)
    return np.asarray(out, dtype=np.float64)
