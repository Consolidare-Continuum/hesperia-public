# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
KME — Primitive Metric Calculator.
Computes LD, COH, NC, PR, PV, CI from ActiveGraph and DomainConstants. All outputs in [0, 1]. Deterministic.
"""

from __future__ import annotations

import math
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.domain.models import ActiveGraph, DomainConstants


def clamp01(x: float) -> float:
    """Clamp to [0, 1]."""
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def positive_or_one(x: float) -> float:
    """Safe positive constant: x <= 0 -> 1.0."""
    return 1.0 if x <= 0.0 else x


def sorted_node_ids(graph: "ActiveGraph") -> list[str]:
    """Canonical sorted list of node ids."""
    return sorted(graph.nodes.keys())


def build_adjacency(graph: "ActiveGraph") -> dict[str, set[str]]:
    """Undirected adjacency: node_id -> set of neighbor ids. Self-loops skipped."""
    adj: dict[str, set[str]] = {nid: set() for nid in graph.nodes}
    for e in graph.edges:
        a, b = e.source_concept_id, e.target_concept_id
        if a == b:
            continue
        if a not in adj or b not in adj:
            continue
        adj[a].add(b)
        adj[b].add(a)
    return adj


def compute_nc(graph: "ActiveGraph", constants: "DomainConstants") -> float:
    """NC = n/N (NodeCoverage)."""
    n = len(graph.nodes)
    N = constants.domain_node_count
    if N <= 0:
        return 0.0
    return clamp01((float(n)) / (float(N)))


def compute_ci(graph: "ActiveGraph") -> float:
    """CI = normalized HHI (ConcentrationIndex). n<=1 -> 0."""
    n = len(graph.nodes)
    if n <= 1:
        return 0.0
    F = sum(node.hit_count for node in graph.nodes.values() if node.hit_count > 0)
    if F <= 0:
        return 0.0
    hhi = 0.0
    for node in graph.nodes.values():
        p = (float(node.hit_count)) / (float(F))
        hhi += p * p
    baseline = 1.0 / (float(n))
    denom = 1.0 - baseline
    if denom <= 0.0:
        return 0.0
    ci = (hhi - baseline) / denom
    return clamp01(ci)


def compute_ld(graph: "ActiveGraph", constants: "DomainConstants") -> float:
    """LD = avgActiveDegree / Deg95 (LogicalDensity). n<=0 -> 0."""
    n = len(graph.nodes)
    m = len(graph.edges)
    Deg95 = positive_or_one(constants.domain_degree_p95)
    if n <= 0:
        return 0.0
    avg_active_degree = (2.0 * float(m)) / float(n)
    ld = avg_active_degree / Deg95
    return clamp01(ld)


def largest_component_size(graph: "ActiveGraph") -> int:
    """Size of largest connected component. Deterministic DFS."""
    adj = build_adjacency(graph)
    visited: set[str] = set()
    largest = 0
    node_ids = sorted_node_ids(graph)
    for start in node_ids:
        if start in visited:
            continue
        size = 0
        stack: deque[str] = deque([start])
        while stack:
            v = stack.pop()
            if v in visited:
                continue
            visited.add(v)
            size += 1
            nbs = sorted(adj.get(v, set()))
            for nb in nbs:
                if nb not in visited:
                    stack.append(nb)
        if size > largest:
            largest = size
    return largest


def count_triangles(graph: "ActiveGraph") -> int:
    """Count triangles. Deterministic: triple (i,j,k) over sorted ids."""
    adj = build_adjacency(graph)
    ids = sorted_node_ids(graph)
    triangles = 0
    for i in range(len(ids)):
        a = ids[i]
        for j in range(i + 1, len(ids)):
            b = ids[j]
            if b not in adj.get(a, set()):
                continue
            for k in range(j + 1, len(ids)):
                c = ids[k]
                if c not in adj.get(a, set()):
                    continue
                if c not in adj.get(b, set()):
                    continue
                triangles += 1
    return triangles


def count_connected_triplets(graph: "ActiveGraph") -> int:
    """Sum over nodes of C(deg(v), 2)."""
    adj = build_adjacency(graph)
    total = 0
    for node_id in sorted_node_ids(graph):
        d = len(adj.get(node_id, set()))
        if d >= 2:
            total += (d * (d - 1)) // 2
    return total


def compute_coh(graph: "ActiveGraph") -> float:
    """COH = 0.6*Conn + 0.4*Trans. n<=0 or n<3 -> 0 (tiny-graph override)."""
    n = len(graph.nodes)
    if n <= 0:
        return 0.0
    if n < 3:
        return 0.0
    largest = largest_component_size(graph)
    conn = (float(largest)) / (float(n))
    tri = count_triangles(graph)
    trip = count_connected_triplets(graph)
    trans = (3.0 * float(tri)) / float(trip) if trip > 0 else 0.0
    coh = 0.6 * conn + 0.4 * trans
    return clamp01(coh)


def select_anchor_ids(graph: "ActiveGraph") -> list[str]:
    """k = max(1, ceil(0.10*n)); top k by descending p_i, tie-break ascending conceptId."""
    n = len(graph.nodes)
    if n <= 0:
        return []
    F = sum(node.hit_count for node in graph.nodes.values() if node.hit_count > 0)
    k = max(1, int(math.ceil(0.10 * n)))
    if F <= 0:
        ids = sorted_node_ids(graph)
        return ids[: min(k, len(ids))]
    nodes_list = list(graph.nodes.values())
    nodes_list.sort(
        key=lambda node: (-((float(node.hit_count)) / (float(F))), node.concept_id),
    )
    return [nodes_list[i].concept_id for i in range(min(k, len(nodes_list)))]


def multi_source_distances(graph: "ActiveGraph", anchor_ids: list[str]) -> dict[str, int]:
    """BFS from all anchors (sorted). Returns shortest distance to nearest anchor per node."""
    adj = build_adjacency(graph)
    dist: dict[str, int] = {}
    queue: deque[str] = deque()
    sorted_anchors = sorted(anchor_ids)
    for a in sorted_anchors:
        if a not in graph.nodes:
            continue
        dist[a] = 0
        queue.append(a)
    while queue:
        v = queue.popleft()
        nbs = sorted(adj.get(v, set()))
        for nb in nbs:
            if nb not in dist:
                dist[nb] = dist[v] + 1
                queue.append(nb)
    return dist


def compute_pr(graph: "ActiveGraph", constants: "DomainConstants") -> float:
    """PR = (1/(|V_reach|*Dist95)) * sum d(v,S). Non-anchors only, reachable."""
    n = len(graph.nodes)
    if n <= 0:
        return 0.0
    Dist95 = positive_or_one(constants.domain_distance_p95)
    anchors = select_anchor_ids(graph)
    if not anchors:
        return 0.0
    anchor_set = set(anchors)
    dist = multi_source_distances(graph, anchors)
    total = 0.0
    count = 0
    for node_id in sorted_node_ids(graph):
        if node_id in anchor_set:
            continue
        d = dist.get(node_id)
        if d is None:
            continue
        total += d
        count += 1
    if count <= 0:
        return 0.0
    pr = total / (float(count) * Dist95)
    return clamp01(pr)


def compute_pv(graph: "ActiveGraph", constants: "DomainConstants") -> float:
    """PV = sum(d*(v,S)+1) over V_prop, divided by N*(Dist95+1)."""
    n = len(graph.nodes)
    N = constants.domain_node_count
    if n <= 0:
        return 0.0
    if N <= 0:
        return 0.0
    Dist95 = positive_or_one(constants.domain_distance_p95)
    anchors = select_anchor_ids(graph)
    if not anchors:
        return 0.0
    anchor_set = set(anchors)
    dist = multi_source_distances(graph, anchors)
    shell_mass = 0.0
    prop_count = 0
    for node_id in sorted_node_ids(graph):
        if node_id in anchor_set:
            shell_mass += 1.0
            prop_count += 1
            continue
        d = dist.get(node_id)
        if d is None:
            continue
        shell_mass += (float(d) + 1.0)
        prop_count += 1
    if prop_count <= 0:
        return 0.0
    pv = shell_mass / (float(N) * (Dist95 + 1.0))
    return clamp01(pv)


def compute_primitives(
    graph: "ActiveGraph | None",
    constants: "DomainConstants | None",
) -> "PrimitiveMetrics":
    """Full primitive calculator. Null or empty graph -> all zeros."""
    from core.domain.models import PrimitiveMetrics

    if graph is None or graph.nodes is None or graph.edges is None or constants is None:
        return PrimitiveMetrics(LD=0.0, COH=0.0, NC=0.0, PR=0.0, PV=0.0, CI=0.0)
    if len(graph.nodes) == 0:
        return PrimitiveMetrics(LD=0.0, COH=0.0, NC=0.0, PR=0.0, PV=0.0, CI=0.0)

    return PrimitiveMetrics(
        LD=compute_ld(graph, constants),
        COH=compute_coh(graph),
        NC=compute_nc(graph, constants),
        PR=compute_pr(graph, constants),
        PV=compute_pv(graph, constants),
        CI=compute_ci(graph),
    )
