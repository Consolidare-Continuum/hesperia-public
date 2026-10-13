# HESPERIA — Tests for LEVEL 13 Activation propagation
"""Intra-area zone spread, bridge spread, normalization."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _embedding():
    from sphere.topology.family_embedding import load_family_embedding_tfp
    return load_family_embedding_tfp()


def test_a3_f1_activates_inner_ring() -> None:
    """Activate A3_F1 (center) → inner_ring families get 0.25 * score."""
    from sphere.topology.activation_propagation import propagate_within_area

    embedding = _embedding()
    family_scores = {"A3_F1": 0.8}
    out = propagate_within_area("A3", family_scores, embedding)
    # A3 center = F1; inner_ring = F2, F3, F5, F6, F11, F14
    assert out["A3_F1"] == 0.8
    # Each inner_ring family gets 0.8 * 0.25 = 0.2
    for fid in ("A3_F2", "A3_F3", "A3_F5", "A3_F6", "A3_F11", "A3_F14"):
        assert out.get(fid, 0) >= 0.18, f"{fid} should get center→inner spread"
    assert out.get("A3_F2", 0) == 0.2


def test_a3_f6_bridge_to_a2() -> None:
    """Activate A3_F6 → bridge spreads to A2 (e.g. A2_F3)."""
    from sphere.topology.activation_propagation import propagate_activation

    embedding = _embedding()
    activation = {"families": {"A3_F6": 0.8}, "areas": {"A3": 0.8}}
    out = propagate_activation(activation, embedding, propagation_trace=True)
    # Bridge A3_F6 → A2_F3 (from embedding bridges)
    assert "A2_F3" in out["families"] or any(k.startswith("A2_") for k in out["families"]), "bridge should add A2 family"
    assert out["families"].get("A2_F3", 0) >= 0.17  # 0.8 * 0.22


def test_a2_f5_bridge_to_a3_f1() -> None:
    """Activate A2_F5 → bridge to A3_F1."""
    from sphere.topology.activation_propagation import propagate_activation

    embedding = _embedding()
    activation = {"families": {"A2_F5": 0.8}, "areas": {"A2": 0.8}}
    out = propagate_activation(activation, embedding)
    # Bridge A2_F5 → A3_F1
    assert out["families"].get("A3_F1", 0) >= 0.17  # 0.8 * 0.22


def test_normalization() -> None:
    """Scores capped at 1.0 after propagation."""
    from sphere.topology.activation_propagation import normalize_scores, propagate_activation

    assert normalize_scores({"a": 0.5, "b": 2.0})["b"] == 1.0
    assert normalize_scores({"a": -0.1})["a"] == 0.0

    embedding = _embedding()
    activation = {"families": {"A3_F1": 2.0, "A3_F2": 1.5}, "areas": {"A3": 2.0}}
    out = propagate_activation(activation, embedding, normalize_after=True)
    for v in out["families"].values():
        assert v <= 1.0 + 1e-6
    for v in out["areas"].values():
        assert v <= 1.0 + 1e-6


def test_propagation_trace_present() -> None:
    """propagate_activation with propagation_trace=True returns trace."""
    from sphere.topology.activation_propagation import propagate_activation

    embedding = _embedding()
    activation = {"families": {"A3_F1": 0.8}, "areas": {"A3": 0.8}}
    out = propagate_activation(activation, embedding, propagation_trace=True)
    assert "propagation_trace" in out
    assert isinstance(out["propagation_trace"], list)


def test_example_from_spec() -> None:
    """Input families = {A3_F1: 0.8} → after propagation A3_F2, A3_F3 ~0.2, A2_F5 ~0.17."""
    from sphere.topology.activation_propagation import propagate_activation

    embedding = _embedding()
    activation = {"families": {"A3_F1": 0.8}, "areas": {"A3": 0.8}}
    out = propagate_activation(activation, embedding)
    assert out["families"]["A3_F1"] == 0.8
    assert out["families"].get("A3_F2", 0) >= 0.19
    assert out["families"].get("A3_F3", 0) >= 0.19
    # Bridge A3_F1 → A2_F5
    assert out["families"].get("A2_F5", 0) >= 0.17
