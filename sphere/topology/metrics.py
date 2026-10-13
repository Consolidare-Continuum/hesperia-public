# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Graph metrics for icosahedral topology: diameter, shortest path distances.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np


def shortest_path_distances(
    adj: np.ndarray,
    source: int,
) -> list[int]:
    """
    BFS from source; return distance to each node (index = node id).
    Unreachable nodes get -1.
    """
    adj = np.asarray(adj)
    n = adj.shape[0]
    dist = [-1] * n
    dist[source] = 0
    q: deque[int] = deque([source])
    while q:
        u = q.popleft()
        for v in range(n):
            if adj[u, v] and dist[v] == -1:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def graph_diameter(adj: np.ndarray) -> int:
    """
    Graph diameter = maximum shortest-path distance over all pairs.
    For icosahedron: diameter = 3.
    """
    adj = np.asarray(adj)
    n = adj.shape[0]
    max_dist = 0
    for s in range(n):
        dists = shortest_path_distances(adj, s)
        for d in dists:
            if d >= 0 and d > max_dist:
                max_dist = d
    return max_dist
