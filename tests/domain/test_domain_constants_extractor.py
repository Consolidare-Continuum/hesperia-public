# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""Tests for Task 1 — Domain Constants Extractor. Deterministic formulas only."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.domain.extractor import (
    bfs_distances,
    build_adjacency,
    clamp_positive,
    compute_degree_p95,
    compute_degrees,
    compute_distance_p95,
    compute_giant_component,
    compute_node_count,
    deterministic_sample,
    extract_constants,
    percentile95,
)
from core.domain.loader import load_domain_graph_from_json, load_frozen_constants
from core.domain.models import DomainConstants, DomainEdge, DomainGraph, DomainNode


def test_clamp_positive() -> None:
    assert clamp_positive(0.0) == 1.0
    assert clamp_positive(-1.0) == 1.0
    assert clamp_positive(3.5) == 3.5


def test_percentile95_empty() -> None:
    assert percentile95([]) == 1.0


def test_percentile95_single() -> None:
    assert percentile95([7]) == 7.0


def test_percentile95_deterministic() -> None:
    # n=20 -> index = ceil(19) - 1 = 18 (0-based)
    vals = list(range(1, 21))
    assert percentile95(vals) == 19.0


def test_compute_node_count_empty() -> None:
    g = DomainGraph(nodes={}, edges=[])
    assert compute_node_count(g) == 0


def test_compute_node_count() -> None:
    g = DomainGraph(
        nodes={"a": DomainNode(concept_id="a"), "b": DomainNode(concept_id="b")},
        edges=[],
    )
    assert compute_node_count(g) == 2


def test_compute_degrees_self_loop_ignored() -> None:
    g = DomainGraph(
        nodes={"a": DomainNode(concept_id="a")},
        edges=[DomainEdge("a", "a", "x")],
    )
    deg = compute_degrees(g)
    assert deg["a"] == 0


def test_compute_degrees_undirected_deduped() -> None:
    g = DomainGraph(
        nodes={"a": DomainNode(concept_id="a"), "b": DomainNode(concept_id="b")},
        edges=[
            DomainEdge("a", "b", "r1"),
            DomainEdge("b", "a", "r2"),
        ],
    )
    deg = compute_degrees(g)
    assert deg["a"] == 1 and deg["b"] == 1


def test_compute_degree_p95_empty_graph() -> None:
    g = DomainGraph(nodes={}, edges=[])
    # no nodes -> degree dict empty -> percentile95([]) -> 1.0 -> clamp 1.0
    assert compute_degree_p95(g) == 1.0


def test_giant_component_single() -> None:
    g = DomainGraph(
        nodes={"a": DomainNode(concept_id="a")},
        edges=[],
    )
    adj = build_adjacency(g)
    giant = compute_giant_component(g)
    assert giant == {"a"}


def test_bfs_distances() -> None:
    adj = {"a": ["b"], "b": ["a", "c"], "c": ["b"]}
    d = bfs_distances(adj, "a")
    assert d == {"a": 0, "b": 1, "c": 2}


def test_deterministic_sample() -> None:
    s = {"z", "a", "m"}
    sample = deterministic_sample(s, 2)
    assert sample == ["a", "m"]


def test_extract_constants_small_graph() -> None:
    path = Path(__file__).resolve().parent / "domain_graph_small.json"
    graph = load_domain_graph_from_json(path)
    c = extract_constants(graph)
    assert c.domain_node_count == 5
    assert c.domain_degree_p95 >= 1.0
    assert c.domain_distance_p95 >= 1.0


def test_extract_constants_deterministic() -> None:
    path = Path(__file__).resolve().parent / "domain_graph_small.json"
    graph = load_domain_graph_from_json(path)
    c1 = extract_constants(graph)
    c2 = extract_constants(graph)
    assert c1.domain_node_count == c2.domain_node_count
    assert c1.domain_degree_p95 == c2.domain_degree_p95
    assert c1.domain_distance_p95 == c2.domain_distance_p95


def test_domain_constants_to_dict() -> None:
    c = DomainConstants(domain_node_count=10, domain_degree_p95=5.0, domain_distance_p95=3.0)
    d = c.to_dict()
    assert d["domain_node_count"] == 10
    assert d["domain_degree_p95"] == 5.0
    assert d["domain_distance_p95"] == 3.0


def test_load_frozen_constants() -> None:
    path = Path(__file__).resolve().parents[1] / ".." / "assets" / "data" / "domain_constants.json"
    path = path.resolve()
    if not path.exists():
        pytest.skip("assets/data/domain_constants.json not present")
    c = load_frozen_constants(path)
    assert c.domain_node_count >= 0
    assert c.domain_degree_p95 >= 1.0
    assert c.domain_distance_p95 >= 1.0
