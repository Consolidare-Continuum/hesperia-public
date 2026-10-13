# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""Tests for Task 3 — Primitive Metric Calculator. Acceptance tests A–E."""

from __future__ import annotations

import math

import pytest

from core.domain.models import (
    ActiveEdge,
    ActiveGraph,
    ActiveNode,
    DomainConstants,
)
from core.domain.primitive_metrics import (
    clamp01,
    compute_ci,
    compute_coh,
    compute_ld,
    compute_nc,
    compute_primitives,
    compute_pr,
    compute_pv,
    count_connected_triplets,
    count_triangles,
    largest_component_size,
    positive_or_one,
)


# Shared constants for tests (N, Deg95, Dist95)
_DEFAULT_CONSTANTS = DomainConstants(
    domain_node_count=100,
    domain_degree_p95=2.0,
    domain_distance_p95=3.0,
)


def _active_graph(nodes: dict[str, int], edges: list[tuple[str, str, str]]) -> ActiveGraph:
    """Build ActiveGraph from node id -> hit_count and list of (source, target, type)."""
    node_map = {cid: ActiveNode(concept_id=cid, hit_count=count) for cid, count in nodes.items()}
    edge_list = [
        ActiveEdge(source_concept_id=a, target_concept_id=b, relation_type=t)
        for a, b, t in edges
    ]
    return ActiveGraph(nodes=node_map, edges=edge_list)


# ---------------------------------------------------------------------------
# Test A — Empty Graph
# ---------------------------------------------------------------------------
def test_empty_graph_all_zeros() -> None:
    """n=0, m=0 -> LD=0, COH=0, NC=0, PR=0, PV=0, CI=0."""
    graph = _active_graph({}, [])
    constants = DomainConstants(domain_node_count=100, domain_degree_p95=2.0, domain_distance_p95=3.0)
    out = compute_primitives(graph, constants)
    assert out.LD == 0.0
    assert out.COH == 0.0
    assert out.NC == 0.0
    assert out.PR == 0.0
    assert out.PV == 0.0
    assert out.CI == 0.0


def test_null_inputs_all_zeros() -> None:
    """Null graph or constants -> all zeros."""
    out = compute_primitives(None, _DEFAULT_CONSTANTS)
    assert out.LD == 0.0 and out.COH == 0.0 and out.NC == 0.0
    assert out.PR == 0.0 and out.PV == 0.0 and out.CI == 0.0
    graph = _active_graph({"a": 1}, [])
    out2 = compute_primitives(graph, None)
    assert out2.LD == 0.0 and out2.CI == 0.0


# ---------------------------------------------------------------------------
# Test B — Single Node
# ---------------------------------------------------------------------------
def test_single_node() -> None:
    """n=1, m=0 -> LD=0, COH=0, NC>0, PR=0, PV>0, CI=0."""
    graph = _active_graph({"a": 1}, [])
    out = compute_primitives(graph, _DEFAULT_CONSTANTS)
    assert out.LD == 0.0
    assert out.COH == 0.0
    assert out.NC > 0
    assert out.NC == pytest.approx(1.0 / 100.0)
    assert out.PR == 0.0  # no non-anchor reachable nodes
    assert out.PV > 0  # anchor occupies shell 0 -> mass 1
    assert out.PV == pytest.approx(1.0 / (100.0 * (3.0 + 1.0)))
    assert out.CI == 0.0  # n<=1


# ---------------------------------------------------------------------------
# Test C — Chain 1-2-3-4-5
# ---------------------------------------------------------------------------
def test_chain_coherence_06() -> None:
    """Chain of 5 nodes: Conn=1, no triangles => Trans=0 => COH=0.6."""
    graph = _active_graph(
        {"1": 1, "2": 1, "3": 1, "4": 1, "5": 1},
        [("1", "2", "r"), ("2", "3", "r"), ("3", "4", "r"), ("4", "5", "r")],
    )
    out = compute_primitives(graph, _DEFAULT_CONSTANTS)
    assert out.LD > 0
    assert out.COH == pytest.approx(0.6)
    assert out.PR > 0
    assert out.PV > 0
    assert 0 <= out.CI <= 1


# ---------------------------------------------------------------------------
# Test D — Triangle
# ---------------------------------------------------------------------------
def test_triangle_coh_one() -> None:
    """Triangle: Conn=1, Trans=1 => COH=1.0."""
    graph = _active_graph(
        {"a": 1, "b": 1, "c": 1},
        [("a", "b", "r"), ("b", "c", "r"), ("a", "c", "r")],
    )
    out = compute_primitives(graph, _DEFAULT_CONSTANTS)
    assert out.LD > 0
    assert out.COH == pytest.approx(1.0)
    assert out.PV > 0
    assert 0 <= out.CI <= 1


# ---------------------------------------------------------------------------
# Test E — Two Disconnected Pairs
# ---------------------------------------------------------------------------
def test_two_disconnected_pairs() -> None:
    """Two pairs: fragmentation => COH < 1, Conn = 2/4 = 0.5."""
    graph = _active_graph(
        {"x": 1, "y": 1, "z": 1, "w": 1},
        [("x", "y", "r"), ("z", "w", "r")],
    )
    out = compute_primitives(graph, _DEFAULT_CONSTANTS)
    assert out.COH < 1.0
    # Largest component size = 2, n = 4 => Conn = 0.5, no triangles => Trans = 0 => COH = 0.6 * 0.5 = 0.3
    assert out.COH == pytest.approx(0.3)
    assert out.PR >= 0
    assert out.PV > 0


# ---------------------------------------------------------------------------
# Utilities and bounds
# ---------------------------------------------------------------------------
def test_clamp01() -> None:
    assert clamp01(-0.1) == 0.0
    assert clamp01(1.5) == 1.0
    assert clamp01(0.5) == 0.5


def test_positive_or_one() -> None:
    assert positive_or_one(0.0) == 1.0
    assert positive_or_one(-1.0) == 1.0
    assert positive_or_one(2.0) == 2.0


def test_all_outputs_in_01() -> None:
    """All primitives must be in [0, 1]."""
    graph = _active_graph(
        {"a": 10, "b": 5, "c": 3},
        [("a", "b", "r"), ("b", "c", "r"), ("a", "c", "r")],
    )
    constants = DomainConstants(domain_node_count=1000, domain_degree_p95=1.0, domain_distance_p95=1.0)
    out = compute_primitives(graph, constants)
    assert 0 <= out.LD <= 1
    assert 0 <= out.COH <= 1
    assert 0 <= out.NC <= 1
    assert 0 <= out.PR <= 1
    assert 0 <= out.PV <= 1
    assert 0 <= out.CI <= 1


def test_ci_zero_when_n1() -> None:
    graph = _active_graph({"a": 5}, [])
    assert compute_ci(graph) == 0.0


def test_ci_uniform() -> None:
    """Uniform hit counts => HHI = 1/n => CI = 0 (after normalization)."""
    graph = _active_graph({"a": 1, "b": 1, "c": 1}, [])
    ci = compute_ci(graph)
    assert ci == pytest.approx(0.0)


def test_nc_ratio() -> None:
    graph = _active_graph({"a": 1, "b": 1}, [])
    constants = DomainConstants(domain_node_count=10, domain_degree_p95=1.0, domain_distance_p95=1.0)
    assert compute_nc(graph, constants) == pytest.approx(0.2)


def test_ld_ratio() -> None:
    # 2 nodes, 1 edge => avg degree = 2*1/2 = 1. Deg95=2 => LD = 0.5
    graph = _active_graph({"a": 1, "b": 1}, [("a", "b", "r")])
    constants = DomainConstants(domain_node_count=10, domain_degree_p95=2.0, domain_distance_p95=1.0)
    assert compute_ld(graph, constants) == pytest.approx(0.5)


def test_triangle_count() -> None:
    graph = _active_graph(
        {"a": 1, "b": 1, "c": 1},
        [("a", "b", "r"), ("b", "c", "r"), ("a", "c", "r")],
    )
    assert count_triangles(graph) == 1
    # Two triangles sharing an edge: a-b-c and a-b-d with c,d both connected to a,b
    graph2 = _active_graph(
        {"a": 1, "b": 1, "c": 1, "d": 1},
        [("a", "b", "r"), ("a", "c", "r"), ("a", "d", "r"), ("b", "c", "r"), ("b", "d", "r")],
    )
    assert count_triangles(graph2) == 2


def test_connected_triplets() -> None:
    # Star: center has deg 3 => C(3,2)=3 triplets
    graph = _active_graph(
        {"c": 1, "1": 1, "2": 1, "3": 1},
        [("c", "1", "r"), ("c", "2", "r"), ("c", "3", "r")],
    )
    assert count_connected_triplets(graph) == 3


def test_largest_component_chain() -> None:
    graph = _active_graph(
        {"1": 1, "2": 1, "3": 1},
        [("1", "2", "r"), ("2", "3", "r")],
    )
    assert largest_component_size(graph) == 3


def test_primitive_metrics_to_dict() -> None:
    from core.domain.models import PrimitiveMetrics

    m = PrimitiveMetrics(LD=0.1, COH=0.2, NC=0.3, PR=0.4, PV=0.5, CI=0.6)
    d = m.to_dict()
    assert d["LD"] == 0.1
    assert list(d.keys()) == ["LD", "COH", "NC", "PR", "PV", "CI"]


def test_determinism_same_input_same_output() -> None:
    graph = _active_graph(
        {"a": 2, "b": 1, "c": 1},
        [("a", "b", "r"), ("b", "c", "r")],
    )
    out1 = compute_primitives(graph, _DEFAULT_CONSTANTS)
    out2 = compute_primitives(graph, _DEFAULT_CONSTANTS)
    assert out1.LD == out2.LD and out1.COH == out2.COH and out1.NC == out2.NC
    assert out1.PR == out2.PR and out1.PV == out2.PV and out1.CI == out2.CI
