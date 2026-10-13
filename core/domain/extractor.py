# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
KME — Domain constants extractor (Task 1).
All formulas from Java-style machine-readable spec; deterministic behavior.
"""

from __future__ import annotations

import math
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.domain.models import DomainGraph


def _canonical_undirected_edges(graph: "DomainGraph") -> list[tuple[str, str]]:
    """Return list of unique undirected edges (no self-loops). Order deterministic for reproducibility."""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for e in graph.edges:
        if e.source_concept_id == e.target_concept_id:
            continue
        a, b = e.source_concept_id, e.target_concept_id
        key = (min(a, b), max(a, b))
        if key not in seen:
            seen.add(key)
            out.append((a, b))
    return out


def clamp_positive(x: float) -> float:
    """Prevent invalid constants: return 1.0 when x <= 0."""
    return 1.0 if x <= 0.0 else x


def compute_node_count(graph: "DomainGraph") -> int:
    """N = |V_R|."""
    if graph is None or graph.nodes is None:
        return 0
    return len(graph.nodes)


def compute_degrees(graph: "DomainGraph") -> dict[str, int]:
    """Degree per node in the undirected canonical graph (self-loops ignored, duplicates count once)."""
    degree: dict[str, int] = {nid: 0 for nid in graph.nodes}
    for a, b in _canonical_undirected_edges(graph):
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
    return degree


def percentile95(values: list[int]) -> float:
    """P95 = sorted_values[ceil(0.95 * n) - 1]. Deterministic."""
    if not values:
        return 1.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    index = int(math.ceil(0.95 * n)) - 1
    if index < 0:
        index = 0
    if index >= n:
        index = n - 1
    return float(sorted_vals[index])


def compute_degree_p95(graph: "DomainGraph") -> float:
    """Deg95 = P95(deg(v) for v in V_R), then clamp positive."""
    degree = compute_degrees(graph)
    deg_values = list(degree.values())
    p95 = percentile95(deg_values)
    return clamp_positive(p95)


def build_adjacency(graph: "DomainGraph") -> dict[str, list[str]]:
    """Undirected adjacency list; self-loops and duplicate edges excluded."""
    adj: dict[str, list[str]] = {nid: [] for nid in graph.nodes}
    for a, b in _canonical_undirected_edges(graph):
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    return adj


def compute_giant_component(graph: "DomainGraph") -> set[str]:
    """Largest connected component via DFS (deterministic order over nodes)."""
    adj = build_adjacency(graph)
    visited: set[str] = set()
    largest: set[str] = set()
    for start in sorted(adj.keys()):
        if start in visited:
            continue
        component: set[str] = set()
        stack: deque[str] = deque([start])
        while stack:
            v = stack.pop()
            if v in visited:
                continue
            visited.add(v)
            component.add(v)
            for nb in adj.get(v, []):
                stack.append(nb)
        if len(component) > len(largest):
            largest = component
    return largest


def bfs_distances(adj: dict[str, list[str]], start: str) -> dict[str, int]:
    """Shortest path distances from start in unweighted graph."""
    dist: dict[str, int] = {}
    queue: deque[str] = deque()
    dist[start] = 0
    queue.append(start)
    while queue:
        v = queue.popleft()
        for nb in adj.get(v, []):
            if nb not in dist:
                dist[nb] = dist[v] + 1
                queue.append(nb)
    return dist


def deterministic_sample(nodes: set[str], limit: int = 100) -> list[str]:
    """Sample min(limit, |nodes|) nodes; deterministic via sorted order."""
    lst = sorted(nodes)
    n = min(limit, len(lst))
    return lst[:n]


def compute_distance_p95(graph: "DomainGraph") -> float:
    """Dist95 = P95 of shortest-path distances in giant component (sampled starts)."""
    adj = build_adjacency(graph)
    giant = compute_giant_component(graph)
    sample = deterministic_sample(giant, 100)
    distances: list[int] = []
    for start in sample:
        dist = bfs_distances(adj, start)
        for node in giant:
            if node in dist:
                d = dist[node]
                if d > 0:
                    distances.append(d)
    if not distances:
        return 1.0
    p95 = percentile95(distances)
    return clamp_positive(p95)


def extract_constants(graph: "DomainGraph") -> "DomainConstants":
    """Compute and return the three domain constants from the reference graph."""
    from core.domain.models import DomainConstants

    return DomainConstants(
        domain_node_count=compute_node_count(graph),
        domain_degree_p95=compute_degree_p95(graph),
        domain_distance_p95=compute_distance_p95(graph),
    )
