# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""Tests for Task 2 — Active Graph Canonicalizer. Deterministic construction."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.domain import (
    build_active_graph,
    load_domain_graph_from_json,
)
from core.domain.active_graph import (
    build_active_edges,
    build_active_nodes,
    domain_has_edge,
)
from core.domain.models import (
    ActiveEdge,
    ActiveNode,
    ConceptHit,
    DomainEdge,
    DomainGraph,
    DomainNode,
    RelationCandidate,
)


def _domain_fixture() -> DomainGraph:
    """Domain with contract_law, legal_obligation, law and two edges."""
    return DomainGraph(
        nodes={
            "contract_law": DomainNode(concept_id="contract_law"),
            "legal_obligation": DomainNode(concept_id="legal_obligation"),
            "law": DomainNode(concept_id="law"),
        },
        edges=[
            DomainEdge("contract_law", "law", "is_subdomain"),
            DomainEdge("contract_law", "legal_obligation", "defines"),
        ],
    )


def test_domain_has_edge() -> None:
    domain = _domain_fixture()
    assert domain_has_edge(domain, "contract_law", "law", "is_subdomain") is True
    assert domain_has_edge(domain, "law", "contract_law", "is_subdomain") is True
    assert domain_has_edge(domain, "contract_law", "law", "other") is False
    assert domain_has_edge(domain, "contract_law", "legal_obligation", "defines") is True
    assert domain_has_edge(domain, "law", "legal_obligation", "defines") is False


def test_build_active_nodes_only_domain_concepts() -> None:
    domain = _domain_fixture()
    hits = [
        ConceptHit("contract_law", 0),
        ConceptHit("unknown_concept", 1),
        ConceptHit("contract_law", 2),
        ConceptHit("law", 3),
    ]
    nodes = build_active_nodes(hits, domain)
    assert set(nodes.keys()) == {"contract_law", "law"}
    assert nodes["contract_law"].hit_count == 2
    assert nodes["law"].hit_count == 1


def test_build_active_edges_canonical_order_and_domain_check() -> None:
    domain = _domain_fixture()
    relations = [
        RelationCandidate("contract_law", "law", "is_subdomain"),
        RelationCandidate("law", "contract_law", "is_subdomain"),  # duplicate when canonicalized
        RelationCandidate("contract_law", "legal_obligation", "defines"),
        RelationCandidate("contract_law", "law", "other"),  # not in domain
    ]
    edges = build_active_edges(relations, domain)
    assert len(edges) == 2
    # Canonical: source <= target
    sources = {e.source_concept_id for e in edges}
    targets = {e.target_concept_id for e in edges}
    assert "contract_law" in sources
    assert "law" in targets or "law" in sources
    keys = {f"{e.source_concept_id}|{e.target_concept_id}|{e.relation_type}" for e in edges}
    assert len(keys) == 2


def test_build_active_edges_self_loop_dropped() -> None:
    domain = DomainGraph(
        nodes={"x": DomainNode(concept_id="x")},
        edges=[DomainEdge("x", "x", "self")],
    )
    # Domain has self-loop but we don't add self-loops to active graph
    relations = [RelationCandidate("x", "x", "self")]
    edges = build_active_edges(relations, domain)
    assert len(edges) == 0


def test_build_active_graph_spec_example() -> None:
    domain = _domain_fixture()
    hits = [
        ConceptHit("contract_law", 0),
        ConceptHit("contract_law", 1),
        ConceptHit("contract_law", 2),
        ConceptHit("legal_obligation", 3),
        ConceptHit("law", 4),
    ]
    relations = [
        RelationCandidate("contract_law", "law", "is_subdomain"),
        RelationCandidate("contract_law", "legal_obligation", "defines"),
    ]
    graph = build_active_graph(hits, relations, domain)
    assert graph.nodes["contract_law"].hit_count == 3
    assert graph.nodes["legal_obligation"].hit_count == 1
    assert graph.nodes["law"].hit_count == 1
    assert len(graph.edges) == 2
    edge_types = {(e.source_concept_id, e.target_concept_id, e.relation_type) for e in graph.edges}
    assert ("contract_law", "law", "is_subdomain") in edge_types
    assert ("contract_law", "legal_obligation", "defines") in edge_types


def test_build_active_graph_deterministic_ordering() -> None:
    domain = _domain_fixture()
    hits = [ConceptHit("law", 0), ConceptHit("contract_law", 1)]
    relations = [RelationCandidate("contract_law", "law", "is_subdomain")]
    graph = build_active_graph(hits, relations, domain)
    node_ids = list(graph.nodes.keys())
    assert node_ids == sorted(node_ids)
    for i in range(len(graph.edges) - 1):
        e1, e2 = graph.edges[i], graph.edges[i + 1]
        t1 = (e1.source_concept_id, e1.target_concept_id, e1.relation_type)
        t2 = (e2.source_concept_id, e2.target_concept_id, e2.relation_type)
        assert t1 <= t2


def test_build_active_graph_empty_hits() -> None:
    domain = _domain_fixture()
    graph = build_active_graph([], [], domain)
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0


def test_build_active_graph_no_valid_relations() -> None:
    domain = _domain_fixture()
    hits = [ConceptHit("contract_law", 0), ConceptHit("law", 1)]
    relations = [
        RelationCandidate("contract_law", "legal_obligation", "nonexistent_type"),
    ]
    graph = build_active_graph(hits, relations, domain)
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 0


def test_active_graph_to_dict() -> None:
    graph = build_active_graph(
        [ConceptHit("contract_law", 0), ConceptHit("law", 1)],
        [RelationCandidate("contract_law", "law", "is_subdomain")],
        _domain_fixture(),
    )
    d = graph.to_dict()
    assert "nodes" in d and "edges" in d
    assert d["nodes"]["contract_law"]["hitCount"] == 1
    assert d["nodes"]["law"]["hitCount"] == 1
    assert len(d["edges"]) == 1
    assert d["edges"][0]["source"] == "contract_law" and d["edges"][0]["target"] == "law"
    assert d["edges"][0]["type"] == "is_subdomain"


def test_build_active_graph_from_json_fixture() -> None:
    path = Path(__file__).resolve().parent / "domain_graph_contract_law.json"
    domain = load_domain_graph_from_json(path)
    hits = [
        ConceptHit("contract_law", 0),
        ConceptHit("legal_obligation", 1),
        ConceptHit("law", 2),
    ]
    relations = [
        RelationCandidate("contract_law", "law", "is_subdomain"),
        RelationCandidate("contract_law", "legal_obligation", "defines"),
    ]
    graph = build_active_graph(hits, relations, domain)
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2


def test_determinism_same_input_same_output() -> None:
    domain = _domain_fixture()
    hits = [
        ConceptHit("contract_law", 0),
        ConceptHit("law", 1),
        ConceptHit("contract_law", 2),
    ]
    relations = [
        RelationCandidate("law", "contract_law", "is_subdomain"),
        RelationCandidate("contract_law", "legal_obligation", "defines"),
    ]
    g1 = build_active_graph(hits, relations, domain)
    g2 = build_active_graph(hits, relations, domain)
    assert list(g1.nodes.keys()) == list(g2.nodes.keys())
    for cid in g1.nodes:
        assert g1.nodes[cid].hit_count == g2.nodes[cid].hit_count
    assert len(g1.edges) == len(g2.edges)
    for e1, e2 in zip(g1.edges, g2.edges):
        assert e1.source_concept_id == e2.source_concept_id
        assert e1.target_concept_id == e2.target_concept_id
        assert e1.relation_type == e2.relation_type
