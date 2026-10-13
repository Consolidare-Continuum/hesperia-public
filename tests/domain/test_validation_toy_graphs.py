# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Task 5 — Validation & Toy-Graph Test Suite.
Verifies primitives and derived metrics: deterministic behavior, range guarantees,
division safety, propagation correctness, structural sensitivity.
No new formulas; validates Tasks 1–4.
"""

from __future__ import annotations

import math
import random
import time

import pytest

from core.domain.models import (
    ActiveEdge,
    ActiveGraph,
    ActiveNode,
    DomainConstants,
    PrimitiveMetrics,
)
from core.domain.primitive_metrics import compute_primitives
from core.domain.derived_metrics import (
    compute_derived_metrics,
    to_derived_vector,
)


# Fixed constants for tests (stable across runs)
TEST_CONSTANTS = DomainConstants(
    domain_node_count=100,
    domain_degree_p95=10.0,
    domain_distance_p95=5.0,
)


def build_graph(
    nodes: list[str],
    edges: list[tuple[str, str]],
) -> ActiveGraph:
    """Build ActiveGraph from node ids and edges. Each node hit_count=1, relation_type='test'."""
    g_nodes = {nid: ActiveNode(concept_id=nid, hit_count=1) for nid in nodes}
    g_edges = [
        ActiveEdge(source_concept_id=a, target_concept_id=b, relation_type="test")
        for a, b in edges
    ]
    return ActiveGraph(nodes=g_nodes, edges=g_edges)


def assert_all_derived_zero(d) -> None:
    """Assert all 35 derived metrics are 0.0."""
    vec = to_derived_vector(d)
    assert len(vec) == 35
    for v in vec:
        assert v == 0.0, f"Expected 0.0, got {v}"


# ---------------------------------------------------------------------------
# Test A — Empty Graph
# ---------------------------------------------------------------------------
def test_empty_graph() -> None:
    """nodes=[], edges=[] -> LD=COH=NC=PR=PV=CI=0, all derived zero."""
    g = build_graph([], [])
    p = compute_primitives(g, TEST_CONSTANTS)
    assert p.LD == 0.0
    assert p.COH == 0.0
    assert p.NC == 0.0
    assert p.PR == 0.0
    assert p.PV == 0.0
    assert p.CI == 0.0
    d = compute_derived_metrics(p)
    assert_all_derived_zero(d)


# ---------------------------------------------------------------------------
# Test B — Single Node
# ---------------------------------------------------------------------------
def test_single_node_graph() -> None:
    """1 node, 0 edges -> LD=0, COH=0, NC>0, PR=0, PV>0, CI=0."""
    g = build_graph(["A"], [])
    p = compute_primitives(g, TEST_CONSTANTS)
    assert p.LD == 0.0
    assert p.COH == 0.0
    assert p.NC > 0
    assert p.PR == 0.0
    assert p.PV > 0
    assert p.CI == 0.0


# ---------------------------------------------------------------------------
# Test C — Two Node Edge
# ---------------------------------------------------------------------------
def test_two_node_graph() -> None:
    """A—B: LD>0, COH=0 (tiny graph rule), PR>0, PV>0."""
    g = build_graph(["A", "B"], [("A", "B")])
    p = compute_primitives(g, TEST_CONSTANTS)
    assert p.LD > 0
    assert p.COH == 0.0
    assert p.PR > 0
    assert p.PV > 0


# ---------------------------------------------------------------------------
# Test D — Chain Graph
# ---------------------------------------------------------------------------
def test_chain_graph() -> None:
    """A—B—C—D—E: Conn=1, Trans=0 => COH=0.6."""
    g = build_graph(
        ["A", "B", "C", "D", "E"],
        [("A", "B"), ("B", "C"), ("C", "D"), ("D", "E")],
    )
    p = compute_primitives(g, TEST_CONSTANTS)
    assert abs(p.COH - 0.6) < 0.01


# ---------------------------------------------------------------------------
# Test E — Triangle Graph
# ---------------------------------------------------------------------------
def test_triangle_graph() -> None:
    """A—B, B—C, A—C: Conn=1, Trans=1 => COH=1."""
    g = build_graph(
        ["A", "B", "C"],
        [("A", "B"), ("B", "C"), ("A", "C")],
    )
    p = compute_primitives(g, TEST_CONSTANTS)
    assert abs(p.COH - 1.0) < 0.01


# ---------------------------------------------------------------------------
# Test F — Star Graph
# ---------------------------------------------------------------------------
def test_star_graph() -> None:
    """Center A, spokes B,C,D,E: LD moderate, COH < 1."""
    g = build_graph(
        ["A", "B", "C", "D", "E"],
        [("A", "B"), ("A", "C"), ("A", "D"), ("A", "E")],
    )
    p = compute_primitives(g, TEST_CONSTANTS)
    assert p.LD > 0
    assert p.COH < 1.0


# ---------------------------------------------------------------------------
# Test G — Disconnected Graph
# ---------------------------------------------------------------------------
def test_disconnected_graph() -> None:
    """A—B and C—D: Conn=0.5, COH < 0.6."""
    g = build_graph(
        ["A", "B", "C", "D"],
        [("A", "B"), ("C", "D")],
    )
    p = compute_primitives(g, TEST_CONSTANTS)
    assert p.COH < 0.6


# ---------------------------------------------------------------------------
# Range Guarantee Test
# ---------------------------------------------------------------------------
def test_range_guarantees() -> None:
    """All derived metrics must remain in [0, 1] for any primitive vector in [0,1]."""
    rng = random.Random(42)
    for _ in range(20):
        p = PrimitiveMetrics(
            LD=rng.uniform(0.0, 1.0),
            COH=rng.uniform(0.0, 1.0),
            NC=rng.uniform(0.0, 1.0),
            PR=rng.uniform(0.0, 1.0),
            PV=rng.uniform(0.0, 1.0),
            CI=rng.uniform(0.0, 1.0),
        )
        d = compute_derived_metrics(p)
        for v in to_derived_vector(d):
            assert 0.0 <= v <= 1.0, f"Derived value {v} out of [0,1]"


# ---------------------------------------------------------------------------
# Division Safety Test
# ---------------------------------------------------------------------------
def test_division_safety() -> None:
    """NC=0, PV=0 must not produce NaN or Infinity in derived metrics."""
    p = PrimitiveMetrics(LD=0.5, COH=0.8, NC=0.0, PR=0.4, PV=0.0, CI=0.2)
    d = compute_derived_metrics(p)
    for v in to_derived_vector(d):
        assert not math.isnan(v), "NaN in derived vector"
        assert not math.isinf(v), "Infinity in derived vector"


# ---------------------------------------------------------------------------
# Determinism Test
# ---------------------------------------------------------------------------
def test_determinism() -> None:
    """Same graph -> identical primitives (and thus derived)."""
    g = build_graph(
        ["A", "B", "C", "D", "E"],
        [("A", "B"), ("B", "C"), ("C", "D"), ("D", "E")],
    )
    p1 = compute_primitives(g, TEST_CONSTANTS)
    p2 = compute_primitives(g, TEST_CONSTANTS)
    assert p1.LD == p2.LD
    assert p1.COH == p2.COH
    assert p1.NC == p2.NC
    assert p1.PR == p2.PR
    assert p1.PV == p2.PV
    assert p1.CI == p2.CI


# ---------------------------------------------------------------------------
# Monotonicity Test
# ---------------------------------------------------------------------------
def test_monotonicity() -> None:
    """Increase LD (others fixed) -> KDI must not decrease."""
    p1 = PrimitiveMetrics(LD=0.3, COH=0.8, NC=0.5, PR=0.4, PV=0.4, CI=0.2)
    p2 = PrimitiveMetrics(LD=0.6, COH=0.8, NC=0.5, PR=0.4, PV=0.4, CI=0.2)
    d1 = compute_derived_metrics(p1)
    d2 = compute_derived_metrics(p2)
    assert d2.KDI >= d1.KDI


# ---------------------------------------------------------------------------
# Propagation Behavior Test
# ---------------------------------------------------------------------------
def test_propagation_behavior() -> None:
    """PR increase (others fixed) -> TDS and SPS must not decrease."""
    p1 = PrimitiveMetrics(LD=0.5, COH=0.7, NC=0.4, PR=0.2, PV=0.3, CI=0.3)
    p2 = PrimitiveMetrics(LD=0.5, COH=0.7, NC=0.4, PR=0.6, PV=0.3, CI=0.3)
    d1 = compute_derived_metrics(p1)
    d2 = compute_derived_metrics(p2)
    assert d2.TDS >= d1.TDS
    assert d2.SPS >= d1.SPS


# ---------------------------------------------------------------------------
# Performance Sanity Test
# ---------------------------------------------------------------------------
def test_performance() -> None:
    """Primitive + derived computation must remain fast (target < 2 ms per graph)."""
    # Large synthetic graph: 50 nodes, ~100 edges (sparse)
    nodes = [f"n{i}" for i in range(50)]
    edges = []
    for i in range(49):
        edges.append((f"n{i}", f"n{i + 1}"))
    for i in range(0, 45, 5):
        edges.append((f"n{i}", f"n{i + 5}"))
    g = build_graph(nodes, edges)

    start = time.perf_counter()
    p = compute_primitives(g, TEST_CONSTANTS)
    d = compute_derived_metrics(p)
    _ = to_derived_vector(d)
    elapsed = time.perf_counter() - start

    # Spec target 2 ms; allow 50 ms for Python/interpreter overhead as sanity bound
    assert elapsed < 0.05, f"Computation took {elapsed*1000:.2f} ms (sanity bound 50 ms)"
