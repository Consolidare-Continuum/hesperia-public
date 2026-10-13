"""DLCR symbolic hex ids → integer cell indices (bounded substrate phase).

Full 72k Hesperia substrate is documented in ``docs/TOPOLOGY_INVARIANTS.md``.
This module maps curator anchors ``HX-NNNN`` to contiguous indices for dynamics adapters.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from core.dynamics.constants import get_constant


def load_hex_index_map(path: str | Path) -> dict[str, int]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("hex_index_map must be a JSON object")
    return {str(k): int(v) for k, v in data.items()}


def symbolic_hex_to_cell_id(symbol: str, index_map: dict[str, int]) -> int | None:
    return index_map.get(symbol)


def neighbor_ring_symbols(symbol: str, index_map: dict[str, int], ring: int = 1) -> list[str]:
    """
    Deterministic locality stub (Ethan PO-19): same-cell or adjacent integer index only.

    Full icosahedral graph lives in ``docs/TOPOLOGY_INVARIANTS.md``; bounded DLCR phase
    uses contiguous index adjacency as a stand-in until full lattice wiring.
    """
    if ring < 1:
        return [symbol]
    cid = index_map.get(symbol)
    if cid is None:
        return [symbol]
    inv: dict[int, list[str]] = {}
    for sym, idx in index_map.items():
        inv.setdefault(int(idx), []).append(str(sym))
    out: set[str] = set()
    for delta in range(-ring, ring + 1):
        idx2 = int(cid) + delta
        for s in inv.get(idx2, []):
            out.add(s)
    return sorted(out)


def distance(symbol_i: str, symbol_j: str, index_map: dict[str, int]) -> float:
    ci = index_map.get(symbol_i)
    cj = index_map.get(symbol_j)
    if ci is None or cj is None:
        return float("inf")
    return float(abs(int(ci) - int(cj)))


def interaction(symbol_i: str, symbol_j: str, index_map: dict[str, int]) -> float:
    d = distance(symbol_i, symbol_j, index_map)
    if math.isinf(d):
        return 0.0
    cutoff_radius = float(get_constant("propagation.cutoff_radius", 6))
    if d > cutoff_radius:
        return 0.0
    k = float(get_constant("propagation.distance_decay_k", 0.55))
    return math.exp(-k * d)
