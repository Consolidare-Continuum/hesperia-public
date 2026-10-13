# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Shannon structural entropy over distributions.
Deterministic; zero probabilities ignored. Pure numerical operations only.
"""

from __future__ import annotations

import math

import numpy as np

from core.math.basic_stats import clamp01


def compute_entropy(vector: np.ndarray | list[float]) -> float:
    """
    Shannon entropy (base 2) over a non-negative distribution.

    Formula:
      p_i = vector[i] / sum(vector)
      entropy = - Σ (p_i * log2(p_i))   for p_i > 0

    Zero probabilities are ignored. If total mass is zero, returns 0.0.
    Deterministic floating precision.
    """
    arr = np.asarray(vector, dtype=np.float64)
    if arr.size == 0:
        return 0.0
    if np.any(arr < 0):
        raise ValueError("Entropy input must be non-negative")
    total = float(np.sum(arr))
    if total <= 0:
        return 0.0
    probs = arr / total
    out = 0.0
    for i in range(len(probs)):
        if probs[i] > 0:
            out -= probs[i] * math.log2(probs[i])
    return float(out)


def compute_normalized_entropy(vector: np.ndarray | list[float]) -> float:
    """
    Normalized entropy: entropy / log2(N), where N = len(vector).
    Range [0, 1]. Returns 0.0 if N <= 1 or total mass is zero.
    """
    arr = np.asarray(vector, dtype=np.float64)
    N = len(arr)
    if N <= 1:
        return 0.0
    H = compute_entropy(arr)
    if H <= 0:
        return 0.0
    return float(H / math.log2(N))


def compute_entropy_nats(vector: np.ndarray | list[float]) -> float:
    """
    Shannon entropy (natural log / nats) over a non-negative distribution.

    Formula:
      p_i = vector[i] / sum(vector)
      entropy = - Σ (p_i * ln(p_i))   for p_i > 0

    Zero probabilities are ignored. If total mass is zero, returns 0.0.
    Distinct from compute_entropy (base-2, for normalized/bits use) — this is the
    raw natural-log form needed by callers (e.g. GTP CoherenceField Psi_ent) that
    do not divide by log(N).

    Graduated to core 2026-07-31 (was sphere/topology/gtp/coherence.py's inline
    math.log entropy sum). Deliberately built on Python's built-in sum() rather
    than numpy or a manual accumulation loop: this must stay bit-exact with the
    original inline formula for the GTP gold-matrix fixtures, and both np.sum's
    pairwise summation and a naive running-total loop round differently in the
    last bit than sum()'s compensated summation (Python 3.12+) for 300-element
    vectors.
    """
    vals = [float(x) for x in vector]
    if not vals:
        return 0.0
    if any(v < 0 for v in vals):
        raise ValueError("Entropy input must be non-negative")
    total = sum(vals)
    if total <= 0:
        return 0.0
    return -sum((v / total) * math.log(v / total) for v in vals if v > 0.0)


def compute_normalized_entropy_from_weights(weights: dict[str, float], *, eps: float = 1e-15) -> float:
    """
    Normalized entropy (natural-log form) over a keyed weight distribution, clamped to [0,1].
    Near-zero weights (<=eps) are excluded before normalizing; log argument is epsilon-smoothed.

    Graduated to core 2026-07-31 (was hesperia.extensions.triz.contradiction_uncertainty.
    _entropy_normalized — mathematically equivalent to compute_normalized_entropy's ratio
    (log base cancels in H/H_max) but with different edge-case handling: dict-keyed input,
    near-zero-weight filtering, and epsilon smoothing inside the log. Kept as a distinct
    function rather than merged, to preserve exact existing numeric behavior.
    """
    vals = [max(0.0, float(v)) for v in weights.values() if float(v) > eps]
    if not vals:
        return 0.0
    s = sum(vals)
    if s <= eps:
        return 0.0
    ps = [v / s for v in vals]
    h = -sum(p * math.log(p + eps) for p in ps)
    h_max = math.log(len(ps)) if len(ps) > 1 else 1.0
    return clamp01(h / h_max) if h_max > eps else 0.0
