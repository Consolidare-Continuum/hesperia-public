# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Generic graph algorithms: BFS shortest path and adjacency-derived neighbor maps.

Graduated to core 2026-07-31 (was the pure-algorithm portion of
hesperia/extensions/triz/topology_metrics.py). These functions take an adjacency
structure as input and have no coupling to sphere/TRIZ loaders or guards — the
sphere-loading + TRIZ-guard wrapper that produces that adjacency stays in
hesperia/extensions/triz/topology_metrics.py, which now calls these functions.
"""

from __future__ import annotations

from collections import deque


def neighbors_from_adjacency(adj: tuple[tuple[int, ...], ...]) -> dict[int, list[int]]:
    n = len(adj)
    out: dict[int, list[int]] = {}
    for i in range(n):
        out[i] = sorted(j for j in range(n) if adj[i][j] == 1)
    return out


def graph_distance(
    node_a: int,
    node_b: int,
    neighbor_map: dict[int, tuple[int, ...]] | dict[int, list[int]],
    *,
    not_found_distance: int,
) -> int:
    """Shortest path length between node_a and node_b via BFS on neighbor_map. 0 = same node."""
    if node_a == node_b:
        return 0
    nm = {k: list(v) for k, v in neighbor_map.items()}
    if node_a not in nm or node_b not in nm:
        return not_found_distance
    q = deque([(node_a, 0)])
    seen = {node_a}
    while q:
        u, d = q.popleft()
        if u == node_b:
            return d
        for v in nm.get(u, ()):
            if v not in seen:
                seen.add(v)
                q.append((v, d + 1))
    return not_found_distance


def locality_score(distance: int) -> float:
    """1/(1+d): high when local (small distance), low when far apart."""
    return round(1.0 / (1.0 + float(distance)), 6)


def are_adjacent(node_a: int, node_b: int, distance: int) -> bool:
    return node_a != node_b and distance == 1


__all__ = [
    "neighbors_from_adjacency",
    "graph_distance",
    "locality_score",
    "are_adjacent",
]
