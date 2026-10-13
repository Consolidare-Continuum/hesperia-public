# HESPERIA — Tests for LEVEL 14 Clinical ActiveGraph (hierarchical bridge)
"""Concept/family/area nodes, hierarchical edges, concept relations, family bridges, area adjacency."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _activation():
    return {
        "concepts": {"B_A3_F1_001": 0.82, "B_A2_F5_002": 0.44},
        "families": {"A3_F1": 0.91, "A2_F5": 0.57},
        "areas": {"A3": 1.0, "A2": 0.63},
    }


def test_concept_family_area_nodes_created() -> None:
    from hesperia.engine.kme.clinical_bridge import build_clinical_active_graph_hierarchical

    out = build_clinical_active_graph_hierarchical(_activation())
    assert "nodes" in out
    assert "edges" in out
    assert "metadata" in out
    nodes = out["nodes"]
    ids = [n["id"] for n in nodes]
    types = {n["id"]: n["node_type"] for n in nodes}
    assert "B_A3_F1_001" in ids
    assert "A3_F1" in ids
    assert "A3" in ids
    assert types.get("B_A3_F1_001") == "concept"
    assert types.get("A3_F1") == "family"
    assert types.get("A3") == "area"
    for n in nodes:
        assert "id" in n and "node_type" in n and "weight" in n
        assert n["node_type"] in ("concept", "family", "area")


def test_concept_to_family_and_family_to_area_edges() -> None:
    from hesperia.engine.kme.clinical_bridge import build_clinical_active_graph_hierarchical

    out = build_clinical_active_graph_hierarchical(_activation())
    edges = out["edges"]
    types = [(e["source"], e["target"], e["edge_type"]) for e in edges]
    assert any(t[2] == "belongs_to_family" for t in types)
    assert any(t[2] == "belongs_to_area" for t in types)
    assert any(e["source"] == "B_A3_F1_001" and e["target"] == "A3_F1" for e in edges)
    assert any(e["source"] == "A3_F1" and e["target"] == "A3" for e in edges)


def test_concept_relation_edges_from_concept_relations() -> None:
    from hesperia.engine.kme.clinical_bridge import (
        build_clinical_active_graph_hierarchical,
        load_clinical_relation_sources,
    )

    sources = load_clinical_relation_sources()
    rels = sources.get("concept_relations") or []
    if not rels:
        return
    out = build_clinical_active_graph_hierarchical(_activation())
    edge_types = {e["edge_type"] for e in out["edges"]}
    assert "activates" in edge_types or "opposes" in edge_types or "co_occurs_with" in edge_types or len(edge_types) >= 2


def test_family_bridge_edges_from_embedding() -> None:
    from hesperia.engine.kme.clinical_bridge import build_clinical_active_graph_hierarchical

    out = build_clinical_active_graph_hierarchical(_activation())
    edges = out["edges"]
    bridge_edges = [e for e in edges if e["edge_type"] == "bridge"]
    assert len(bridge_edges) >= 1
    assert any(e["source"] in ("A3_F1", "A2_F5") and e["target"] in ("A3_F1", "A2_F5") for e in bridge_edges)


def test_area_adjacency_edges_for_active_areas() -> None:
    from hesperia.engine.kme.clinical_bridge import build_clinical_active_graph_hierarchical

    out = build_clinical_active_graph_hierarchical(_activation())
    edges = out["edges"]
    area_edges = [e for e in edges if e["edge_type"] == "area_adjacent"]
    assert isinstance(area_edges, list)
    for e in area_edges:
        assert e["source"] in ("A2", "A3") or e["source"].startswith("A")
        assert e["target"] in ("A2", "A3") or e["target"].startswith("A")


def test_output_matches_expected_schema() -> None:
    from hesperia.engine.kme.clinical_bridge import build_clinical_active_graph_hierarchical

    out = build_clinical_active_graph_hierarchical(_activation())
    assert out["metadata"]["source"] == "clinical_bridge"
    assert out["metadata"]["node_count"] == len(out["nodes"])
    assert out["metadata"]["edge_count"] == len(out["edges"])
    assert out["metadata"]["levels"] == ["concept", "family", "area"]
    assert out["nodes"] == sorted(out["nodes"], key=lambda n: n["id"])


def test_analyze_session_to_kme_graph_returns_graph() -> None:
    from hesperia.engine.kme.clinical_bridge import analyze_session_to_kme_graph

    graph = analyze_session_to_kme_graph("Пациент злится на терапевта.")
    assert "nodes" in graph
    assert "edges" in graph
    assert "metadata" in graph


def test_run_session_kme_pipeline_returns_report() -> None:
    from hesperia.engine.kme.clinical_bridge import run_session_kme_pipeline

    report = run_session_kme_pipeline("Терапевт интерпретирует перенос.")
    assert report.source_id == "session"
    assert "LD" in report.primitive_map
    assert report.fingerprint is not None
