# Time series, hex volatility, smoothing

from __future__ import annotations

from core.domain.models import ActiveEdge, ActiveGraph, ActiveNode
from hesperia.extensions.triz.contradiction_engine import detect_contradictions
from hesperia.extensions.triz.hex_signals import aggregate_hex_pressure, hex_volatility_index
from hesperia.extensions.triz.signal_normalization import exponential_smoothing
from hesperia.extensions.triz.time_series import (
    clear_history,
    exponential_smooth_series,
    persistent_contradictions,
    update_signal_history,
)


def test_exponential_smoothing() -> None:
    s = exponential_smoothing([1.0, 2.0, 3.0], alpha=0.5)
    assert len(s) == 3
    assert s[0] == 1.0


def test_hex_volatility() -> None:
    prev = {1: 0.5, 2: 0.2}
    curr = {1: 0.8, 2: 0.2}
    v = hex_volatility_index(prev, curr)
    assert v[1] == round(0.3, 6)
    assert 2 not in v or v.get(2, 0) == 0


def test_hex_pressure_aggregate() -> None:
    g = ActiveGraph(
        nodes={"a": ActiveNode("a", 5), "b": ActiveNode("b", 5)},
        edges=[ActiveEdge("a", "b", "conflict")],
    )
    xs = detect_contradictions(g, min_score=0.0)
    m = {"a": {"area_id": 0, "family_id": 0, "hex_id": 100}, "b": {"area_id": 0, "family_id": 1, "hex_id": 101}}
    p = aggregate_hex_pressure(None, xs, m)
    assert p[100] > 0 and p[101] > 0


def test_persistent_contradictions_three_runs() -> None:
    clear_history("sig_test")
    snap = [{"concept_a": "u", "concept_b": "v", "score": 0.5}]
    for _ in range(3):
        update_signal_history("sig_test", {"contradictions": snap, "innovation_clusters": [], "narratives": []})
    keys = persistent_contradictions("sig_test", min_runs=3)
    assert "u|v" in keys
    clear_history("sig_test")


def test_time_series_smooth() -> None:
    assert exponential_smooth_series([10.0, 20.0], 0.3)[-1] > 10.0
