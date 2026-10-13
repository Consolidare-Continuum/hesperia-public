"""METRIC-35 — family_graph shortest-path helper."""
from __future__ import annotations

from runtime.services.family_graph import (
    family_graph_edge_for_path_metric,
    family_graph_shortest_path_cost,
)


def test_same_family_zero_cost() -> None:
    emb = {
        "A2": {
            "center": ["F1"],
            "inner_ring": ["F2"],
            "middle_ring": [],
            "outer_ring": [],
        },
        "bridges": [],
    }
    assert family_graph_shortest_path_cost("A2_F1", "A2_F1", emb) == 0.0


def test_zone_step_positive_cost() -> None:
    emb = {
        "A2": {
            "center": ["F1"],
            "inner_ring": ["F2"],
            "middle_ring": [],
            "outer_ring": [],
        },
        "bridges": [],
    }
    cost = family_graph_shortest_path_cost("A2_F1", "A2_F2", emb)
    assert cost is not None and cost > 0.0


def test_path_metric_edge_shape() -> None:
    emb = {
        "A2": {"center": ["F1"], "inner_ring": ["F2"], "middle_ring": [], "outer_ring": []},
        "bridges": [],
    }
    edge = family_graph_edge_for_path_metric("A2_F1", "A2_F2", emb)
    assert edge is not None
    assert edge["layer"] == "family_graph"
    assert "zone_path_cost" in edge
