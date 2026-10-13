# Family-level contradiction clustering

from __future__ import annotations

from core.domain.models import ActiveEdge, ActiveGraph, ActiveNode
from hesperia.extensions.triz.contradiction_engine import detect_contradictions
from hesperia.extensions.triz.family_clustering import (
    cluster_contradictions_by_area_family,
    cluster_contradictions_by_family,
    get_conflict_hotspots,
)
from hesperia.extensions.triz.triz_classifier import classify_contradictions


def _graph_and_mapping():
    g = ActiveGraph(
        nodes={"p": ActiveNode("p", 5), "q": ActiveNode("q", 5)},
        edges=[ActiveEdge("p", "q", "conflict")],
    )
    m = {
        "p": {"area_id": 3, "family_id": 8, "hex_id": None},
        "q": {"area_id": 7, "family_id": 14, "hex_id": None},
    }
    return g, m


def test_cluster_by_family_pair() -> None:
    g, m = _graph_and_mapping()
    xs = detect_contradictions(g, min_score=0.0)
    classify_contradictions(xs)
    rows = cluster_contradictions_by_family(xs, m)
    assert len(rows) == 1
    assert rows[0]["count"] == 1
    assert set(rows[0]["family_pair"]) == {8, 14}


def test_hotspots_sorted() -> None:
    g, m = _graph_and_mapping()
    xs = detect_contradictions(g, min_score=0.0)
    hs = get_conflict_hotspots(xs, m, top_n=5)
    assert hs and hs[0]["hotspot_score"] > 0


def test_area_family_cluster_labels() -> None:
    g, m = _graph_and_mapping()
    xs = detect_contradictions(g, min_score=0.0)
    af = cluster_contradictions_by_area_family(xs, m)
    assert af[0]["area_a"] in (3, 7)
    assert af[0]["area_b"] in (3, 7)
