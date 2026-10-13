# TRIZ pipeline — contradiction, novelty, propagation

from __future__ import annotations

from hesperia.extensions.triz.contradiction_engine import (
    build_contradiction_signals,
    enumerate_contradiction_pairs,
)
from hesperia.extensions.triz.models import ConceptActivation, ConceptRelation, MatrixCoordinate
from hesperia.extensions.triz.novelty_engine import detect_concept_clusters, score_innovation_clusters
from hesperia.extensions.triz.propagation_engine import aggregate_area_activation, propagate_activation
from hesperia.extensions.triz.topology_binding import bind_concepts_to_coordinates
from hesperia.extensions.triz.topology_metrics import neighbors_from_adjacency
from hesperia.extensions.triz.triz_pipeline import run_triz_analysis


def test_contradiction_two_opposite_concepts() -> None:
    acts = [
        ConceptActivation("x", 1.0, MatrixCoordinate(0, 0, None)),
        ConceptActivation("y", 1.0, MatrixCoordinate(1, 1, None)),
    ]
    rels = [ConceptRelation("x", "y", "negation", 1.0)]
    raw = enumerate_contradiction_pairs(acts, rels)
    assert len(raw) == 1
    assert raw[0][2] == 1.0
    coords = bind_concepts_to_coordinates(acts)
    sigs = build_contradiction_signals(acts, rels, coords, min_score=0.01)
    assert len(sigs) == 1
    assert sigs[0].concept_a == "x" and sigs[0].concept_b == "y"


def test_innovation_rare_cluster_higher_score() -> None:
    coords = {
        "a": MatrixCoordinate(0, 0, None),
        "b": MatrixCoordinate(11, 5, None),
        "c": MatrixCoordinate(3, 2, None),
    }
    clusters_tight = [["a", "b"]]
    clusters_wide = [["a", "b", "c"]]
    density = 0.5
    s_tight = score_innovation_clusters(
        clusters_tight, density, coords, total_concepts=10, final_activations={"a": 1.0, "b": 1.0}
    )
    s_wide = score_innovation_clusters(
        clusters_wide, density, coords, total_concepts=10, final_activations={"a": 1.0, "b": 1.0, "c": 1.0}
    )
    assert s_tight[0].rarity > s_wide[0].rarity


def test_narrative_propagation_adjacent_areas_only() -> None:
    from hesperia.extensions.triz.topology_metrics import canonical_area_adjacency

    neighbors = neighbors_from_adjacency(canonical_area_adjacency())
    acts = [
        ConceptActivation("c0", 1.0, MatrixCoordinate(0, 0, None)),
    ]
    agg = aggregate_area_activation(acts)
    assert 0 in agg
    prop = propagate_activation(agg, neighbors, steps=1, damping=0.05)
    nbs = neighbors.get(0, [])
    for nb in nbs:
        assert prop.get(nb, 0.0) >= 0.0
    assert prop[0] > 0


def test_run_triz_analysis_sorted_and_rounded() -> None:
    from hesperia.extensions.triz.topology_metrics import canonical_area_adjacency

    neighbors = neighbors_from_adjacency(canonical_area_adjacency())
    acts = [
        ConceptActivation("a", 0.9, MatrixCoordinate(0, 1, None)),
        ConceptActivation("b", 0.8, MatrixCoordinate(1, 2, None)),
    ]
    rels = [ConceptRelation("a", "b", "conflict", 1.0)]
    out = run_triz_analysis(acts, rels, neighbors, family_count=240)
    assert out.contradictions == sorted(out.contradictions, key=lambda x: (-x.score, x.concept_a, x.concept_b))
    for c in out.contradictions:
        assert c.score == round(c.score, 6)


def test_detect_concept_clusters_from_relations() -> None:
    rels = [
        ConceptRelation("a", "b", "rel", 1.0),
        ConceptRelation("b", "c", "rel", 1.0),
        ConceptRelation("d", "e", "rel", 1.0),
    ]
    cl = detect_concept_clusters(rels)
    flat = {x for g in cl for x in g}
    assert flat == {"a", "b", "c", "d", "e"}
    assert len([g for g in cl if "a" in g]) == 1
    assert set(next(g for g in cl if "a" in g)) == {"a", "b", "c"}
