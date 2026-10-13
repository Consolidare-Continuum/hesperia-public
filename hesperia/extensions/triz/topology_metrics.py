# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Canonical 12-area icosahedral metrics: adjacency load, shortest-path distance, locality.

MOVED 2026-07-31: the pure graph algorithms (BFS distance, neighbor maps, locality score)
now live in core.math.graph_topology — no domain semantics, no sphere/TRIZ coupling. This
module keeps the sphere-loading + TRIZ-guard wrapper (canonical_area_adjacency and friends)
that produces the 12-area adjacency data, and calls the core functions with it. Public API
unchanged — every function here has the same name and signature as before the split.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from core.math.graph_topology import (
    are_adjacent,
    graph_distance,
    locality_score,
    neighbors_from_adjacency,
)

# Lazy import numpy only when loading file


@lru_cache(maxsize=1)
def _canonical_area_adjacency_default() -> tuple[tuple[int, ...], ...]:
    from sphere.topology.topology_loader import load_area_adjacency as _load_adj
    from hesperia.extensions.triz.guards import guard_adjacency_immutable

    adj = _load_adj(None)
    guard_adjacency_immutable(adj)
    return tuple(tuple(int(x) for x in row) for row in adj.tolist())


def load_area_adjacency(data_root: Path | None = None) -> tuple[tuple[int, ...], ...]:
    """Alias for Task 12.1 — canonical icosahedral area adjacency (read-only rows)."""
    return canonical_area_adjacency(data_root)


def canonical_area_adjacency(data_root: Path | None = None) -> tuple[tuple[int, ...], ...]:
    """
    Load canonical 12×12 area adjacency from HESPERIA topology data (read-only).
    """
    if data_root is None:
        return _canonical_area_adjacency_default()
    from sphere.topology.topology_loader import load_area_adjacency as _load_adj
    from hesperia.extensions.triz.guards import guard_adjacency_immutable

    adj = _load_adj(data_root)
    guard_adjacency_immutable(adj)
    return tuple(tuple(int(x) for x in row) for row in adj.tolist())


@lru_cache(maxsize=1)
def _neighbor_map() -> dict[int, tuple[int, ...]]:
    adj = canonical_area_adjacency()
    nm = neighbors_from_adjacency(adj)
    return {k: tuple(v) for k, v in sorted(nm.items())}


def area_distance(area_a: int, area_b: int) -> int:
    """Shortest path length on icosahedral area graph; 0 = same, 1 = adjacent."""
    return graph_distance(area_a, area_b, _neighbor_map(), not_found_distance=12)


def contradiction_locality_score(area_a: int, area_b: int) -> float:
    """1/(1+d): local contradiction high, cross-domain spread low."""
    return locality_score(area_distance(area_a, area_b))


def areas_are_adjacent(area_a: int, area_b: int) -> bool:
    return are_adjacent(area_a, area_b, area_distance(area_a, area_b))


def get_area_neighbors() -> dict[int, list[int]]:
    """Canonical adjacency lists (area index → neighbor areas)."""
    return {k: list(v) for k, v in _neighbor_map().items()}


def get_area_adjacency() -> list[list[int]]:
    """12×12 binary adjacency matrix (canonical icosahedral); same source as propagation TRIZ."""
    adj = canonical_area_adjacency()
    return [list(row) for row in adj]
