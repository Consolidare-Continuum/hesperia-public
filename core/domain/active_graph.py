# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
KME — Active Graph Canonicalizer.
Deterministic construction of text-activated semantic graph A = (V_A, E_A).
Same text + same domain graph → identical active graph.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.domain.models import (
        ActiveEdge,
        ActiveGraph,
        ActiveNode,
        ConceptHit,
        DomainGraph,
        RelationCandidate,
    )


def _min_str(a: str, b: str) -> str:
    return a if a <= b else b


def _max_str(a: str, b: str) -> str:
    return b if a <= b else a


def _domain_edge_set(domain: "DomainGraph") -> set[tuple[str, str, str]]:
    """Set of (source, target, relation_type) with source <= target, no self-loops."""
    out: set[tuple[str, str, str]] = set()
    for e in domain.edges:
        if e.source_concept_id == e.target_concept_id:
            continue
        s = _min_str(e.source_concept_id, e.target_concept_id)
        t = _max_str(e.source_concept_id, e.target_concept_id)
        out.add((s, t, e.relation_type))
    return out


def domain_has_edge(domain: "DomainGraph", source: str, target: str, relation_type: str) -> bool:
    """Check if domain graph contains this edge (undirected, canonical order)."""
    s = _min_str(source, target)
    t = _max_str(source, target)
    return (s, t, relation_type) in _domain_edge_set(domain)


def build_active_nodes(
    hits: list["ConceptHit"],
    domain: "DomainGraph",
) -> dict[str, "ActiveNode"]:
    """Rule 1: Only domain concepts allowed. f_i = count of concept occurrences."""
    from core.domain.models import ActiveNode

    nodes: dict[str, ActiveNode] = {}
    for hit in hits:
        if hit.concept_id not in domain.nodes:
            continue
        if hit.concept_id not in nodes:
            nodes[hit.concept_id] = ActiveNode(concept_id=hit.concept_id, hit_count=0)
        nodes[hit.concept_id].hit_count += 1
    return nodes


def build_active_edges(
    relations: list["RelationCandidate"],
    domain: "DomainGraph",
) -> list["ActiveEdge"]:
    """Rule 2: Edge must exist in domain. Rule 3–5: canonical order, no self-loops, collapse duplicates."""
    from core.domain.models import ActiveEdge

    domain_edges = _domain_edge_set(domain)
    edges: list[ActiveEdge] = []
    seen: set[str] = set()
    for rc in relations:
        if rc.concept_a not in domain.nodes or rc.concept_b not in domain.nodes:
            continue
        source = _min_str(rc.concept_a, rc.concept_b)
        target = _max_str(rc.concept_a, rc.concept_b)
        if source == target:
            continue
        if (source, target, rc.relation_type) not in domain_edges:
            continue
        key = f"{source}|{target}|{rc.relation_type}"
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            ActiveEdge(
                source_concept_id=source,
                target_concept_id=target,
                relation_type=rc.relation_type,
            )
        )
    return edges


def build_active_graph(
    hits: list["ConceptHit"],
    relations: list["RelationCandidate"],
    domain: "DomainGraph",
) -> "ActiveGraph":
    """Assemble active graph, apply deterministic ordering, run integrity checks."""
    from core.domain.models import ActiveGraph

    if domain is None or domain.nodes is None:
        return ActiveGraph(nodes={}, edges=[])
    nodes = build_active_nodes(hits, domain)
    edges = build_active_edges(relations, domain)

    nodes_sorted = dict(sorted(nodes.items()))
    edges_sorted = sorted(
        edges,
        key=lambda e: (e.source_concept_id, e.target_concept_id, e.relation_type),
    )

    graph = ActiveGraph(nodes=nodes_sorted, edges=edges_sorted)

    assert len(graph.nodes) <= len(domain.nodes), "|V_A| <= |V_R|"
    assert len(graph.edges) <= len(domain.edges), "|E_A| <= |E_R|"
    edge_keys = {f"{e.source_concept_id}|{e.target_concept_id}|{e.relation_type}" for e in graph.edges}
    assert len(edge_keys) == len(graph.edges), "No duplicate edges"

    return graph
