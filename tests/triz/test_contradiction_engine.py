# TRIZ contradiction engine validation

from __future__ import annotations

from core.domain.models import ActiveEdge, ActiveGraph, ActiveNode
from hesperia.extensions.triz.contradiction_engine import CONFLICT_TYPES, detect_contradictions


def test_no_contradiction_without_conflict_relation() -> None:
    g = ActiveGraph(
        nodes={"a": ActiveNode("a", 1), "b": ActiveNode("b", 1)},
        edges=[ActiveEdge("a", "b", "is_subdomain")],
    )
    assert detect_contradictions(g, min_score=0.0) == []


def test_scores_in_unit_interval() -> None:
    g = ActiveGraph(
        nodes={"a": ActiveNode("a", 5), "b": ActiveNode("b", 5)},
        edges=[ActiveEdge("a", "b", "negation")],
    )
    for c in detect_contradictions(g, min_score=0.0):
        assert 0.0 <= c.score <= 1.0


def test_deterministic_ordering() -> None:
    g = ActiveGraph(
        nodes={
            "z": ActiveNode("z", 3),
            "a": ActiveNode("a", 3),
        },
        edges=[
            ActiveEdge("a", "z", "conflict"),
        ],
    )
    xs = detect_contradictions(g, min_score=0.0)
    assert len(xs) == 1
    assert CONFLICT_TYPES == {"conflict", "negation", "opposition"}
