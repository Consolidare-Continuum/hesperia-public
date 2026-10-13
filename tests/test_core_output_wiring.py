from __future__ import annotations

from core.domain.models import ConceptHit, DomainConstants, DomainEdge, DomainGraph, DomainNode, RelationCandidate
from core.domain.pipeline import metric_report_to_dict, run_document
from hesperia.engine.kme.clinical_bridge import run_kme_from_activation


def _domain() -> DomainGraph:
    nodes = {
        "A": DomainNode(concept_id="A"),
        "B": DomainNode(concept_id="B"),
        "C": DomainNode(concept_id="C"),
    }
    edges = [
        DomainEdge("A", "B", "r"),
        DomainEdge("B", "C", "r"),
        DomainEdge("A", "C", "r"),
    ]
    return DomainGraph(nodes=nodes, edges=edges)


def _constants() -> DomainConstants:
    return DomainConstants(
        domain_node_count=100,
        domain_degree_p95=10.0,
        domain_distance_p95=5.0,
    )


def _hits() -> list[ConceptHit]:
    return [
        ConceptHit("A", 0),
        ConceptHit("B", 1),
        ConceptHit("C", 2),
        ConceptHit("A", 3),
    ]


def _relations() -> list[RelationCandidate]:
    return [
        RelationCandidate("A", "B", "r"),
        RelationCandidate("B", "C", "r"),
        RelationCandidate("A", "C", "r"),
    ]


def test_core_pipeline_report_maps_follow_fingerprint_source_of_truth() -> None:
    report = run_document(
        _domain(),
        _constants(),
        "paper_001",
        _hits(),
        _relations(),
        domain_release="test_v0_1",
    )

    assert report.primitive_map == report.fingerprint.primitive_map
    assert report.derived_map == report.fingerprint.derived_map

    payload = metric_report_to_dict(report)
    assert payload["primitives"] == payload["fingerprint"]["primitiveMap"]
    assert payload["derived"] == payload["fingerprint"]["derivedMap"]
    assert payload["fingerprint"]["sourceId"] == payload["sourceId"]
    assert payload["fingerprint"]["domainRelease"] == "test_v0_1"
    assert payload["fingerprint"]["fingerprintVersion"] == "hesperia_fp_v0_1"
    assert payload["fingerprint"]["vectorHash"]


def test_clinical_bridge_report_maps_follow_fingerprint_source_of_truth() -> None:
    report = run_kme_from_activation(
        {
            "concepts": {"A": 0.75, "B": 0.50, "C": 0.25},
            "concept_to_area": {"A": 1, "B": 2, "C": 3},
            "concept_to_family": {"A": 11, "B": 12, "C": 13},
        },
        source_id="session_001",
        domain_graph=_domain(),
        domain_release="bridge_v0_1",
    )

    assert report.primitive_map == report.fingerprint.primitive_map
    assert report.derived_map == report.fingerprint.derived_map

    payload = metric_report_to_dict(report)
    assert payload["primitives"] == payload["fingerprint"]["primitiveMap"]
    assert payload["derived"] == payload["fingerprint"]["derivedMap"]
    assert payload["fingerprint"]["sourceId"] == "session_001"
    assert payload["fingerprint"]["domainRelease"] == "bridge_v0_1"
    assert "triz" in payload


def test_metric_report_contract_uses_current_json_keys() -> None:
    report = run_document(
        _domain(),
        _constants(),
        "paper_002",
        _hits(),
        _relations(),
    )

    payload = metric_report_to_dict(report)
    # core.domain.pipeline.run_document no longer computes triz_signals (core has
    # zero relation to TRIZ or any other module); "triz" is only added by the
    # hesperia.engine.kme.clinical_bridge integration layer, exercised separately
    # in test_clinical_bridge_report_maps_follow_fingerprint_source_of_truth above.
    assert sorted(payload.keys()) == ["derived", "fingerprint", "primitives", "sourceId"]
    assert "primitiveMap" in payload["fingerprint"]
    assert "derivedMap" in payload["fingerprint"]
    assert "metricValues" in payload["fingerprint"]
    assert len(payload["fingerprint"]["metricValues"]) == 41
