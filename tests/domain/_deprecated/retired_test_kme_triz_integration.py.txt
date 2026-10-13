# KME pipeline (hesperia.engine.kme) + TRIZ integration

from __future__ import annotations

from core.domain.models import (
    ConceptHit,
    DomainConstants,
    DomainEdge,
    DomainGraph,
    DomainNode,
    RelationCandidate,
)
from core.domain.pipeline import metric_report_to_dict, run_document
from hesperia.extensions.triz.report_extractors import extract_triz_summary
from hesperia.extensions.triz.topology_metrics import get_area_adjacency


def _domain() -> DomainGraph:
    nodes = {
        "contract_law": DomainNode(concept_id="contract_law"),
        "legal_obligation": DomainNode(concept_id="legal_obligation"),
    }
    edges = [
        DomainEdge("contract_law", "legal_obligation", "is_subdomain"),
    ]
    return DomainGraph(nodes=nodes, edges=edges)


def _constants() -> DomainConstants:
    return DomainConstants(domain_node_count=100, domain_degree_p95=10.0, domain_distance_p95=5.0)


def test_metric_report_includes_triz() -> None:
    dg, dc = _domain(), _constants()
    hits = [ConceptHit("contract_law", 0), ConceptHit("legal_obligation", 1)]
    rel = [RelationCandidate("contract_law", "legal_obligation", "is_subdomain")]
    report = run_document(dg, dc, "doc1", hits, rel)
    assert report.triz_signals is not None
    d = metric_report_to_dict(report)
    assert "triz" in d
    assert "contradictions" in d["triz"]
    assert "atomic_metrics" in d["triz"]
    assert "primary_signals" in d["triz"]
    assert "contradiction_density" in d["triz"]["primary_signals"]
    s = extract_triz_summary(report)
    assert s["triz_enabled"] is True


def test_triz_with_concept_topology() -> None:
    dg, dc = _domain(), _constants()
    hits = [ConceptHit("contract_law", 0)]
    rel: list = []
    caf = {"contract_law": ("0", "1")}
    report = run_document(dg, dc, "d2", hits, rel, concept_to_area_family=caf)
    assert report.triz_signals is not None


def test_active_graph_weights() -> None:
    from core.domain.active_graph import build_active_graph

    dg = _domain()
    hits = [ConceptHit("contract_law", 0), ConceptHit("legal_obligation", 1)]
    rel: list = []
    g = build_active_graph(hits, rel, dg)
    w = g.node_weights
    assert len(w) == 2
    assert max(w.values()) <= 1.0


def test_get_area_adjacency_shape() -> None:
    m = get_area_adjacency()
    assert len(m) == 12 and all(len(r) == 12 for r in m)
