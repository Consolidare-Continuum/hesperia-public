from __future__ import annotations

from core.domain.models import ActiveEdge, ActiveGraph, ActiveNode
from hesperia.extensions.triz.commercial_intelligence import (
    build_commercial_intelligence_bundle,
    compare_triz_corpora,
    extract_core_commercial_signals,
)
from hesperia.extensions.triz.direct_outputs import TRIZDirectMetrics
from hesperia.extensions.triz.pipeline import run_triz_layer


def test_commercial_bundle_core_signals() -> None:
    g = ActiveGraph(
        nodes={
            "a": ActiveNode("a", 2),
            "b": ActiveNode("b", 2),
        },
        edges=[ActiveEdge("a", "b", "negation")],
    )
    sig = run_triz_layer(g, None)
    bundle = build_commercial_intelligence_bundle(sig)
    assert bundle["schema_version"] == "commercial_intelligence_v1"
    cs = bundle["core_signals"]
    assert "policy_tension_index" in cs
    assert "policy_coherence_score" in cs
    assert 0.0 <= cs["policy_coherence_score"] <= 1.0
    assert "regulatory_conflict_detector" in bundle["policy_contradiction_products"]
    assert bundle["innovation_intelligence_products"]["innovation_radar"]["cluster_ranking"]


def test_extract_core_from_payload() -> None:
    g = ActiveGraph(nodes={"x": ActiveNode("x", 1)}, edges=[])
    sig = run_triz_layer(g, None)
    triz = sig.to_dict()
    triz["commercial_intelligence"] = build_commercial_intelligence_bundle(sig)
    core = extract_core_commercial_signals(triz)
    assert core["system_tension_index"] >= 0.0


def test_compare_triz_corpora() -> None:
    a = TRIZDirectMetrics(contradiction_density=0.1, innovation_score=0.4, narrative_penetration=0.2, innovation_cluster_count=3)
    b = TRIZDirectMetrics(contradiction_density=0.2, innovation_score=0.6, narrative_penetration=0.5, innovation_cluster_count=5)
    out = compare_triz_corpora(a, b)
    assert out["strategy_divergence_score"] == 0.1
    assert out["innovation_momentum_index"] == 0.2
