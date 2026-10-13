# Topology-bounded propagation

from __future__ import annotations

import json
from pathlib import Path

from core.domain.models import ActiveEdge, ActiveGraph, ActiveNode
from hesperia.extensions.triz.contradiction_engine import detect_contradictions
from hesperia.extensions.triz.propagation_engine import (
    META_AREAS,
    propagate_topology_mode,
)
from hesperia.extensions.triz.topology_metrics import get_area_neighbors


def test_meta_areas_no_lexical_base() -> None:
    g = ActiveGraph(
        nodes={"c": ActiveNode("c", 10)},
        edges=[],
    )
    c2a = {"c": 5}
    c2f = {"c": 120}
    xs = detect_contradictions(g, min_score=0.99)
    r = propagate_topology_mode(g, c2a, c2f, xs)
    assert float(r["area_base"][5]) == 0.0


def test_propagate_area_activation_step_clamped() -> None:
    from hesperia.extensions.triz.propagation_engine import propagate_area_activation

    neighbors = get_area_neighbors()
    base = [0.2] * 12
    base[0] = 0.9
    cur = [0.15] * 12
    cur[0] = 0.95
    nxt = propagate_area_activation(cur, neighbors, base, {1: 0.5}, 0.02)
    assert len(nxt) == 12
    assert all(0.0 <= x <= 1.0 for x in nxt)


def test_topology_mode_fixture_coherent() -> None:
    fix = Path(__file__).resolve().parent / "fixtures" / "coherent.json"
    d = json.loads(fix.read_text(encoding="utf-8"))
    from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete

    ag = active_graph_from_payload(d["active_graph"])
    out = run_triz_analysis_complete(ag, d["topology"], topology_mode=True)
    assert "topology" in out
    assert META_AREAS == {5, 11}
