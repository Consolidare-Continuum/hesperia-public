# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Contradiction density, connected clusters, innovation scoring."""

from __future__ import annotations

from collections import defaultdict

import networkx as nx

from hesperia.extensions.triz.models import (
    ConceptRelation,
    ContradictionSignal,
    InnovationCluster,
    MatrixCoordinate,
)

LOUVAIN_SEED = 42


def compute_contradiction_density(
    contradictions: list[ContradictionSignal],
    relations: list[ConceptRelation],
) -> float:
    if not relations:
        return 0.0
    return round(min(1.0, len(contradictions) / float(len(relations))), 6)


def detect_concept_clusters(relations: list[ConceptRelation]) -> list[list[str]]:
    """Undirected connected components from the relation graph."""
    adj: dict[str, set[str]] = defaultdict(set)
    for r in relations:
        s, t = r.source, r.target
        if s == t:
            continue
        adj[s].add(t)
        adj[t].add(s)
    visited: set[str] = set()
    components: list[list[str]] = []
    for start in sorted(adj.keys()):
        if start in visited:
            continue
        stack = [start]
        comp: list[str] = []
        while stack:
            u = stack.pop()
            if u in visited:
                continue
            visited.add(u)
            comp.append(u)
            for v in sorted(adj[u]):
                if v not in visited:
                    stack.append(v)
        components.append(sorted(comp))
    components.sort(key=lambda c: (c[0] if c else "", len(c), c))
    return components


def score_innovation_clusters(
    clusters: list[list[str]],
    contradiction_density: float,
    concept_coords: dict[str, MatrixCoordinate],
    *,
    total_concepts: int,
    final_activations: dict[str, float] | None = None,
    min_cluster_size: int = 1,
) -> list[InnovationCluster]:
    """
    innovation_score = rarity × contradiction_density × area_reach (capped at 1.0).
    """
    n = max(total_concepts, 1)
    total_act = sum(final_activations.values()) if final_activations else 1.0
    out: list[InnovationCluster] = []
    for idx, concepts in enumerate(clusters):
        if len(concepts) < min_cluster_size:
            continue
        size = len(concepts)
        rarity = min(1.0, 1.0 - (float(size - 1) / float(max(n - 1, 1))))
        areas: set[int] = set()
        for cid in concepts:
            co = concept_coords.get(cid)
            if co is not None and co.area_id >= 0:
                areas.add(co.area_id)
        area_reach = min(1.0, len(areas) / 12.0) if areas else 0.05
        if final_activations:
            cluster_act = sum(final_activations.get(c, 0.0) for c in concepts)
            propagation_reach = min(1.0, cluster_act / max(total_act, 1e-9))
        else:
            propagation_reach = min(1.0, float(size) / float(n))
        raw = rarity * contradiction_density * area_reach
        score = min(1.0, raw * (0.6 + 0.4 * propagation_reach))
        out.append(
            InnovationCluster(
                cluster_id=f"c{idx:04d}",
                concepts=list(concepts),
                rarity=round(rarity, 6),
                contradiction_density=round(float(contradiction_density), 6),
                propagation_reach=round(propagation_reach, 6),
                innovation_score=round(score, 6),
            )
        )
    out.sort(key=lambda x: (-x.innovation_score, x.cluster_id))
    return out


# --- Legacy: Louvain on ActiveGraph (product / time-series) ---

def _norm_activation(graph: object, cid: str) -> float:
    n = graph.nodes.get(cid)
    if not n:
        return 0.0
    mx = max((node.hit_count for node in graph.nodes.values()), default=1)
    mx = max(mx, 1)
    return min(1.0, float(n.hit_count) / float(mx))


def detect_concept_clusters_louvain(active_graph: object) -> list[list[str]]:
    nodes = list(active_graph.nodes.keys())
    if not nodes:
        return []
    G = nx.Graph()
    for cid in nodes:
        G.add_node(cid)
    seen: set[tuple[str, str, str]] = set()
    for e in active_graph.edges:
        u, v = e.source_concept_id, e.target_concept_id
        if u == v or u not in G or v not in G:
            continue
        a, b = (u, v) if u <= v else (v, u)
        key = (a, b, e.relation_type or "")
        if key in seen:
            continue
        seen.add(key)
        w = _norm_activation(active_graph, u) * _norm_activation(active_graph, v)
        w = max(w, 1e-9)
        if G.has_edge(a, b):
            G[a][b]["weight"] = G[a][b]["weight"] + w
        else:
            G.add_edge(a, b, weight=w)
    if G.number_of_edges() == 0:
        return [[n] for n in sorted(nodes)]
    try:
        comms = nx.community.louvain_communities(G, weight="weight", seed=LOUVAIN_SEED)
    except Exception:
        comms = [{n} for n in G.nodes()]
    clusters = [sorted(list(c)) for c in comms]
    clusters.sort(key=lambda c: (c[0] if c else "", len(c), c))
    return clusters


def compute_innovation_clusters(
    active_graph: object,
    final_activations: dict[str, float],
    *,
    min_cluster_size: int = 3,
    min_contradiction_score: float = 0.15,
) -> list[InnovationCluster]:
    """Louvain clusters + innovation score (legacy ActiveGraph path)."""
    from hesperia.extensions.triz.contradiction_engine import build_contradiction_signals
    from hesperia.extensions.triz.topology_binding import bind_concepts_to_coordinates

    rels = [
        ConceptRelation(e.source_concept_id, e.target_concept_id, e.relation_type or "", 1.0)
        for e in active_graph.edges
    ]
    rels.sort(key=lambda r: (r.source, r.target, r.relation_type))
    mx = max((n.hit_count for n in active_graph.nodes.values()), default=1)
    mx = max(mx, 1)
    from hesperia.extensions.triz.models import ConceptActivation, MatrixCoordinate

    acts = [
        ConceptActivation(
            cid,
            min(1.0, float(n.hit_count) / float(mx)),
            MatrixCoordinate(-1, -1, None),
        )
        for cid, n in sorted(active_graph.nodes.items())
    ]
    coords = bind_concepts_to_coordinates(acts)
    sigs = build_contradiction_signals(acts, rels, coords, min_score=min_contradiction_score)
    density = compute_contradiction_density(sigs, rels)
    raw_clusters = detect_concept_clusters_louvain(active_graph)
    return score_innovation_clusters(
        raw_clusters,
        density,
        coords,
        total_concepts=max(len(active_graph.nodes), 1),
        final_activations=final_activations,
        min_cluster_size=min_cluster_size,
    )
