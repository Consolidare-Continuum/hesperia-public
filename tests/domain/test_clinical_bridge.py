# HESPERIA — Tests for clinical activation → KME bridge
"""DomainGraph from Dict-B, ActiveGraph from activation, run_kme_from_activation."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_load_domain_graph_from_dict_b() -> None:
    from hesperia.engine.kme.clinical_bridge import load_domain_graph_from_dict_b

    domain = load_domain_graph_from_dict_b()
    assert domain is not None
    assert len(domain.nodes) > 0
    assert "B_A3_F1_001" in domain.nodes or any("B_A" in n for n in domain.nodes)
    for nid, node in domain.nodes.items():
        assert node.concept_id == nid
    if domain.edges:
        e = domain.edges[0]
        assert e.source_concept_id in domain.nodes
        assert e.target_concept_id in domain.nodes
        assert e.relation_type in ("activates", "opposes", "co_occurs_with", "part_of", "defends_against", "expresses", "observed_in", "is_a")


def test_build_clinical_active_graph_empty() -> None:
    from hesperia.engine.kme.clinical_bridge import build_clinical_active_graph

    out = build_clinical_active_graph({"areas": {}, "families": {}, "concepts": {}})
    assert out is not None
    assert len(out.nodes) == 0
    assert len(out.edges) == 0


def test_build_clinical_active_graph_from_activation() -> None:
    from hesperia.engine.kme.clinical_bridge import build_clinical_active_graph, load_domain_graph_from_dict_b

    domain = load_domain_graph_from_dict_b()
    # Use concept ids that exist in Dict-B (from concept_nodes / relations)
    active_ids = list(domain.nodes.keys())[:5]
    concepts = {cid: 0.5 for cid in active_ids}
    activation = {"areas": {"A3": 0.5}, "families": {}, "concepts": concepts}
    out = build_clinical_active_graph(activation, domain_graph=domain)
    assert len(out.nodes) == len(active_ids)
    for cid in active_ids:
        assert cid in out.nodes
        assert out.nodes[cid].hit_count >= 1
    # Edges: only between active concepts that have a relation in domain
    for e in out.edges:
        assert e.source_concept_id in out.nodes
        assert e.target_concept_id in out.nodes


def test_run_kme_from_activation_returns_report() -> None:
    from hesperia.engine.kme.clinical_bridge import load_domain_graph_from_dict_b, run_kme_from_activation

    domain = load_domain_graph_from_dict_b()
    active_ids = list(domain.nodes.keys())[:8]
    concepts = {cid: 0.3 for cid in active_ids}
    activation = {"areas": {}, "families": {}, "concepts": concepts}
    report = run_kme_from_activation(activation, source_id="test_session", domain_graph=domain)
    assert report.source_id == "test_session"
    assert "LD" in report.primitive_map
    assert "COH" in report.primitive_map
    assert "NC" in report.primitive_map
    assert "PR" in report.primitive_map
    assert "PV" in report.primitive_map
    assert "CI" in report.primitive_map
    assert report.derived_map is not None
    assert report.fingerprint is not None
    assert report.fingerprint.vector_hash


def test_activation_to_hits_and_relations() -> None:
    from hesperia.engine.kme.clinical_bridge import (
        load_domain_graph_from_dict_b,
        activation_to_hits_and_relations,
    )

    domain = load_domain_graph_from_dict_b()
    node_ids = list(domain.nodes.keys())[:3]
    activation = {"concepts": {nid: 0.4 for nid in node_ids}}
    hits, relations = activation_to_hits_and_relations(activation, domain)
    assert len(hits) >= 3
    concept_counts = {}
    for h in hits:
        concept_counts[h.concept_id] = concept_counts.get(h.concept_id, 0) + 1
    for nid in node_ids:
        assert concept_counts.get(nid, 0) >= 1
    for r in relations:
        assert r.concept_a in node_ids
        assert r.concept_b in node_ids
