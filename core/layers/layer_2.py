# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Engine 0.5.0 — Layer-2 (35_SPEC); “v0.4.x” = legacy SPEC-era label only.
25 variables, deterministic, topology-bound. No semantics, no books, no shadow.
Inputs: L1 output (DOMINANT_FAMILY_ID, DOMINANT_AREA_ID), hits[], adjacency, area, F, A, MAX_ALLOWED_DEPTH, eps.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any

from core.contracts.layer_contract import LayerInput, LayerOutput


def build_canonical_stub_adjacency(F: int, A: int) -> list[set[int]]:
    """
    Build a deterministic stub adjacency for F families, A areas.
    Ring within the full family index space: each family f connected to (f-1)%F and (f+1)%F.
    So geometry is a simple ring; area[f] = f // (F//A).
    Caller can replace with real topology (e.g. from invariant_catalog or file).
    """
    adj: list[set[int]] = [set() for _ in range(F)]
    for f in range(F):
        adj[f].add((f - 1) % F)
        adj[f].add((f + 1) % F)
    return adj


def _area_for_family(f: int, F: int, A: int) -> int:
    """area[f] = f // (F//A); 0..A-1."""
    fpa = F // A if A else 24
    return min(f // fpa, A - 1)


def _compute_clustering(adjacency: list[set[int]], v: int, _F: int) -> float:
    """Local clustering coefficient at v. (2*triangles)/(deg*(deg-1)); 0 if deg < 2."""
    N = adjacency[v]
    deg = len(N)
    if deg < 2:
        return 0.0
    triangles = 0
    for a in N:
        for b in N:
            if a < b and b in adjacency[a]:
                triangles += 1
    return (2.0 * triangles) / (deg * (deg - 1))


def compute_L2(
    l1_output: dict[str, Any],
    hits: list[int],
    adjacency: list[set[int]] | None = None,
    area: list[int] | None = None,
    F: int = 288,
    A: int = 12,
    MAX_ALLOWED_DEPTH: int = 8,
    eps: float = 1e-9,
) -> dict[str, Any]:
    """
    Compute Layer-2 25 variables (35_SPEC).
    BFS from DOMINANT_FAMILY_ID up to MAX_ALLOWED_DEPTH; then all traversal metrics.
    If adjacency is None, uses build_canonical_stub_adjacency(F, A).
    If area is None, area[f] = f // (F//A).
    """
    if len(hits) != F:
        raise ValueError(f"hits length must be F={F}, got {len(hits)}")
    if adjacency is None:
        adjacency = build_canonical_stub_adjacency(F, A)
    if len(adjacency) != F:
        raise ValueError(f"adjacency length must be F={F}, got {len(adjacency)}")
    if area is None:
        area = [_area_for_family(f, F, A) for f in range(F)]

    start = int(l1_output["DOMINANT_FAMILY_ID"])
    DOMINANT_AREA_ID = int(l1_output["DOMINANT_AREA_ID"])

    # BFS
    depth = [-1] * F
    parent = [-1] * F
    depth[start] = 0
    q: deque[int] = deque([start])
    visited: list[int] = [start]
    mass_at_depth: list[float] = [0.0] * (MAX_ALLOWED_DEPTH + 1)
    mass_at_depth[0] = float(hits[start])

    while q:
        u = q.popleft()
        d = depth[u]
        if d >= MAX_ALLOWED_DEPTH:
            continue
        for v in adjacency[u]:
            if depth[v] == -1:
                depth[v] = d + 1
                parent[v] = u
                q.append(v)
                visited.append(v)
                if depth[v] <= MAX_ALLOWED_DEPTH:
                    mass_at_depth[depth[v]] += hits[v]

    visited_set = set(visited)
    TOTAL_REACHABLE_NODES = len(visited)

    # 1
    TRAVERSAL_START_FAMILY = start
    # 2
    BASE_NEIGHBOR_COUNT = len(adjacency[start])
    # 3
    ACTIVE_NEIGHBOR_COUNT = sum(1 for n in adjacency[start] if hits[n] > 0)
    # 4
    NEIGHBOR_ACTIVATION_RATIO = ACTIVE_NEIGHBOR_COUNT / (BASE_NEIGHBOR_COUNT + eps)
    # 5
    TRAVERSAL_DEPTH_REACHED = 0
    for d in range(MAX_ALLOWED_DEPTH + 1):
        if mass_at_depth[d] > 0:
            TRAVERSAL_DEPTH_REACHED = d
    # 6 done
    # 7
    REACH_RATIO = TOTAL_REACHABLE_NODES / (F + eps)
    # 8, 9
    dist_sum = 0.0
    MAX_TRAVERSAL_DISTANCE = 0
    for v in visited:
        dist_sum += depth[v]
        if depth[v] > MAX_TRAVERSAL_DISTANCE:
            MAX_TRAVERSAL_DISTANCE = depth[v]
    MEAN_TRAVERSAL_DISTANCE = dist_sum / (TOTAL_REACHABLE_NODES + eps)
    # 10
    TRAVERSAL_RADIUS_RATIO = MAX_TRAVERSAL_DISTANCE / (MAX_ALLOWED_DEPTH + eps)
    # 11 BFS tree edges
    PATH_COUNT = max(0, TOTAL_REACHABLE_NODES - 1)
    # 12
    branch_sum = sum(len(adjacency[v]) for v in visited)
    BRANCHING_FACTOR_MEAN = branch_sum / (TOTAL_REACHABLE_NODES + eps)
    # 13
    LOCAL_CLUSTERING_COEFFICIENT = _compute_clustering(adjacency, start, F)
    # 14
    if TRAVERSAL_DEPTH_REACHED >= 1:
        PROPAGATION_MASS_DECAY = mass_at_depth[TRAVERSAL_DEPTH_REACHED] / (
            mass_at_depth[TRAVERSAL_DEPTH_REACHED - 1] + eps
        )
    else:
        PROPAGATION_MASS_DECAY = 1.0
    # 15
    initial_mass = hits[start]
    total_mass_visited = sum(hits[v] for v in visited)
    MASS_RETENTION_RATIO = total_mass_visited / (initial_mass + eps)
    # 16, 17
    CROSS_AREA_TRAVERSAL_COUNT = sum(1 for v in visited if area[v] != DOMINANT_AREA_ID)
    CROSS_AREA_RATIO = CROSS_AREA_TRAVERSAL_COUNT / (TOTAL_REACHABLE_NODES + eps)
    # 18
    AREA_BOUNDARY_CROSSINGS = sum(
        1 for v in visited if parent[v] >= 0 and area[parent[v]] != area[v]
    )
    # 19
    TRAVERSAL_COMPACTNESS = TOTAL_REACHABLE_NODES / (MAX_TRAVERSAL_DISTANCE + 1)
    # 20, 21 induced subgraph edges
    induced_edges = 0
    for v in visited:
        for u in adjacency[v]:
            if u in visited_set and v < u:
                induced_edges += 1
    used_edges = TOTAL_REACHABLE_NODES - 1
    LOOP_COUNT = max(0, induced_edges - used_edges)
    LOOP_DENSITY = LOOP_COUNT / (TOTAL_REACHABLE_NODES + eps)
    # 22 degree centrality (raw degree per spec)
    centrality_start = len(adjacency[start])
    centrality_sum = sum(len(adjacency[v]) for v in visited)
    mean_centrality = centrality_sum / (TOTAL_REACHABLE_NODES + eps)
    CENTRALITY_SHIFT = abs(centrality_start - mean_centrality)
    # 23
    total_edges_induced = induced_edges
    EDGE_UTILIZATION_RATIO = used_edges / (total_edges_induced + eps)
    # 24 variance of distance from start
    var_sum = sum((depth[v] - MEAN_TRAVERSAL_DISTANCE) ** 2 for v in visited)
    TRAVERSAL_SYMMETRY_INDEX = var_sum / (TOTAL_REACHABLE_NODES + eps)
    # 25
    GEOMETRIC_STABILITY_INDEX = (
        MASS_RETENTION_RATIO
        * max(0.0, 1.0 - CROSS_AREA_RATIO)
        * max(0.0, 1.0 - LOOP_DENSITY)
    )

    # VISITED_IDS: set of family IDs reached in BFS (for L3). MASS_AT_DEPTH: for L6.
    visited_ids = list(visited_set)
    mass_at_depth_list = mass_at_depth[: MAX_ALLOWED_DEPTH + 1]

    return {
        "TRAVERSAL_START_FAMILY": TRAVERSAL_START_FAMILY,
        "BASE_NEIGHBOR_COUNT": BASE_NEIGHBOR_COUNT,
        "ACTIVE_NEIGHBOR_COUNT": ACTIVE_NEIGHBOR_COUNT,
        "NEIGHBOR_ACTIVATION_RATIO": NEIGHBOR_ACTIVATION_RATIO,
        "TRAVERSAL_DEPTH_REACHED": TRAVERSAL_DEPTH_REACHED,
        "TOTAL_REACHABLE_NODES": TOTAL_REACHABLE_NODES,
        "REACH_RATIO": REACH_RATIO,
        "MEAN_TRAVERSAL_DISTANCE": MEAN_TRAVERSAL_DISTANCE,
        "MAX_TRAVERSAL_DISTANCE": MAX_TRAVERSAL_DISTANCE,
        "TRAVERSAL_RADIUS_RATIO": TRAVERSAL_RADIUS_RATIO,
        "PATH_COUNT": PATH_COUNT,
        "BRANCHING_FACTOR_MEAN": BRANCHING_FACTOR_MEAN,
        "LOCAL_CLUSTERING_COEFFICIENT": LOCAL_CLUSTERING_COEFFICIENT,
        "PROPAGATION_MASS_DECAY": PROPAGATION_MASS_DECAY,
        "MASS_RETENTION_RATIO": MASS_RETENTION_RATIO,
        "CROSS_AREA_TRAVERSAL_COUNT": CROSS_AREA_TRAVERSAL_COUNT,
        "CROSS_AREA_RATIO": CROSS_AREA_RATIO,
        "AREA_BOUNDARY_CROSSINGS": AREA_BOUNDARY_CROSSINGS,
        "TRAVERSAL_COMPACTNESS": TRAVERSAL_COMPACTNESS,
        "LOOP_COUNT": LOOP_COUNT,
        "LOOP_DENSITY": LOOP_DENSITY,
        "CENTRALITY_SHIFT": CENTRALITY_SHIFT,
        "EDGE_UTILIZATION_RATIO": EDGE_UTILIZATION_RATIO,
        "TRAVERSAL_SYMMETRY_INDEX": TRAVERSAL_SYMMETRY_INDEX,
        "GEOMETRIC_STABILITY_INDEX": GEOMETRIC_STABILITY_INDEX,
        "VISITED_IDS": visited_ids,
        "MASS_AT_DEPTH": mass_at_depth_list,
    }


def run(input: LayerInput) -> LayerOutput:
    """Layer-2 public entry point. Consumes LayerInput, returns LayerOutput. No other public entry points."""
    t0 = time.perf_counter()
    meta = input.metadata
    layers = meta.get("layers", {})
    l1_output = layers.get(1)
    if not l1_output:
        raise ValueError("Layer 2 requires layer 1 result in input.metadata['layers'][1]")
    F = int(meta.get("F", 288))
    A = int(meta.get("A", 12))
    eps = float(meta.get("eps", 1e-9))
    MAX_ALLOWED_DEPTH = int(meta.get("MAX_ALLOWED_DEPTH", meta.get("defaults", {}).get("MAX_ALLOWED_DEPTH", 8)))
    hits = meta.get("hits")
    if hits is None or len(hits) != F:
        raise ValueError(f"Layer 2 requires metadata['hits'] of length F={F}")
    adjacency = meta.get("adjacency")
    if adjacency is None:
        adjacency = build_canonical_stub_adjacency(F, A)
    result = compute_L2(
        l1_output,
        hits,
        adjacency=adjacency,
        F=F,
        A=A,
        MAX_ALLOWED_DEPTH=MAX_ALLOWED_DEPTH,
        eps=eps,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return LayerOutput(
        layer_id=2,
        result=result,
        diagnostics={"layer_id": 2, "execution_time_ms": round(elapsed_ms, 6)},
    )
