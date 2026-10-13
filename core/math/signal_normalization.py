# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.
#
# Generic time-series smoothing/normalization. Graduated to core 2026-07-31 (was the
# function portion of hesperia/extensions/triz/signal_normalization.py — pure numeric
# transforms, no TRIZ semantics; the domain-specific threshold constants stayed there).

from __future__ import annotations

import math


def exponential_smoothing(series: list[float], alpha: float = 0.3) -> list[float]:
    """EWMA; alpha in (0,1]. First value seeds the smooth."""
    if not series:
        return []
    a = min(1.0, max(1e-9, alpha))
    out = [series[0]]
    for x in series[1:]:
        out.append(a * x + (1.0 - a) * out[-1])
    return out


def moving_average(series: list[float], window: int = 3) -> list[float]:
    """Simple causal moving average; window >= 1."""
    if not series or window < 1:
        return list(series)
    w = min(window, len(series))
    out: list[float] = []
    for i in range(len(series)):
        lo = max(0, i - w + 1)
        chunk = series[lo : i + 1]
        out.append(sum(chunk) / float(len(chunk)))
    return out


def z_score_normalize(series: list[float], eps: float = 1e-9) -> list[float]:
    """Per-sequence z-score; deterministic; empty → []."""
    if not series:
        return []
    mu = sum(series) / float(len(series))
    var = sum((x - mu) ** 2 for x in series) / float(len(series))
    sd = math.sqrt(var + eps)
    return [(x - mu) / sd for x in series]


def sublinear_compress(x: float, compression: float, *, eps: float = 1e-15) -> float:
    """
    Sublinear dampening of an accumulated positive value: x^(1/k) for compression k > 1.
    k <= 1 returns x unchanged. k is clamped to [1.000001, 10.0].

    Graduated to core 2026-07-31 (was the private helper
    hesperia.extensions.triz.contradiction_coupling._smooth_pressure_accum — pure numeric
    transform, no TRIZ semantics, renamed on graduation for generic reuse).
    """
    k = float(compression)
    if k <= 1.0 + eps:
        return float(x)
    return float(x) ** (1.0 / min(max(k, 1.000001), 10.0))


__all__ = [
    "exponential_smoothing",
    "moving_average",
    "z_score_normalize",
    "sublinear_compress",
]
