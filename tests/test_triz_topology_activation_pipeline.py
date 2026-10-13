# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

from hesperia.extensions.triz.topology_activation_pipeline import (
    build_concept_coactivation_graph,
    build_cross_plane_audit,
    build_family_contradiction_matrix,
    concept_id_to_area_family,
    family_conflict_score,
    run_topology_triz_activation,
    topology_mean_max_activation,
    triz_activation_pipeline_fail,
)


def test_concept_id_to_area_family() -> None:
    assert concept_id_to_area_family("B_A1_F8_004") == ("A1", "A1_F8")
    assert concept_id_to_area_family("bad") is None


def test_family_conflict_rules() -> None:
    assert family_conflict_score("A1_F8", "A1_F8") == 0.0
    assert family_conflict_score("A1_F8", "A1_F9") == 0.2
    assert family_conflict_score("A1_F8", "A2_F20") == 1.0
    assert family_conflict_score("A1_F8", "A3_F12") == 0.5


def test_coactivation_and_pipeline() -> None:
    topo = {
        "segments": [
            {
                "concepts": {
                    "B_A1_F8_004": 1.0,
                    "B_A2_F20_002": 0.9,
                    "B_A1_F9_001": 0.5,
                }
            },
            {
                "concepts": {
                    "B_A1_F8_004": 0.8,
                    "B_A2_F20_002": 0.7,
                }
            },
        ],
        "state_sequence": ["A1", "A2", "A3"],
    }
    edges = build_concept_coactivation_graph(topo)
    assert len(edges) >= 1
    assert edges[0]["cooccurrence_count"] >= 1
    fam_keys: set[str] = set()
    for e in edges:
        for cid in (e["concept_i"], e["concept_j"]):
            p = concept_id_to_area_family(cid)
            if p:
                fam_keys.add(p[1])
    mx = build_family_contradiction_matrix(sorted(fam_keys))
    assert mx["A1_F8"]["A2_F20"] == 1.0
    bundle = run_topology_triz_activation(
        topo,
        triz_complete={
            "triz_complete": {
                "innovation_clusters": [
                    {
                        "cluster_id": "c0001",
                        "concepts": ["B_A1_F8_004", "B_A2_F20_002"],
                        "rarity": 0.1,
                        "contradiction_density": 0.0,
                        "propagation_reach": 0.0,
                        "innovation_score": 0.0,
                    }
                ]
            }
        },
    )
    assert bundle["triz_metrics_v1.json"]["contradiction_count"] > 0
    assert bundle["cross_plane_audit.json"]["pass"] is True
    assert not triz_activation_pipeline_fail(bundle["cross_plane_audit.json"])


def test_triz_dead_layer_audit() -> None:
    topo = {
        "segments": [{"concepts": {"B_A1_F8_004": 1.0}}],
        "state_sequence": ["A1"],
    }
    m = {"contradiction_count": 0}
    audit = build_cross_plane_audit(topo, m)
    assert audit["pass"] is False
    assert any(a.get("code") == "TRIZ_DEAD_LAYER" for a in audit["anomalies"])
    assert triz_activation_pipeline_fail(audit) is True


def test_topology_mean_max_activation() -> None:
    topo = {"segments": [{"concepts": {"B_A1_F8_004": 0.2}}, {"concepts": {"B_A2_F20_002": 0.8}}]}
    v = topology_mean_max_activation(topo)
    assert 0.49 < v < 0.51
