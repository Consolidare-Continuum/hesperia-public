"""Central numeric envelope helpers."""

from __future__ import annotations

import math

from core.dynamics.constants import get_constant

EPS = float(get_constant("numeric.eps", 1e-8))
MAX_ENERGY = float(get_constant("numeric.max_energy", 1.0))
MIN_ENERGY = float(get_constant("numeric.min_energy", 0.0))
FLOAT_PRECISION = int(get_constant("numeric.float_precision", 8))


def quantize(value: float) -> float:
    return round(float(value), FLOAT_PRECISION)


def clamp_energy(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return MIN_ENERGY
    if value < MIN_ENERGY:
        return MIN_ENERGY
    if value > MAX_ENERGY:
        return MAX_ENERGY
    return quantize(value)


def clamp_non_negative(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    if value < 0.0:
        return 0.0
    return quantize(value)


def clamp01(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return max(0.0, min(1.0, quantize(value)))

