"""Propagation law: local spread and decay only."""

from __future__ import annotations

import math

from core.hexmap.topology import interaction


def propagation_decay(distance_value: float, k: float) -> float:
    if distance_value < 0:
        return 0.0
    return max(0.0, min(1.0, math.exp(-float(k) * float(distance_value))))


def local_interaction(symbol_i: str, symbol_j: str, index_map: dict[str, int]) -> float:
    return interaction(symbol_i, symbol_j, index_map)

