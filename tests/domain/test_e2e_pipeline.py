# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""E2E Integration — full pipeline test: hits + relations → report with 41 metrics, hash, JSON export."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.domain.models import (
    ConceptHit,
    DocumentInput,
    DomainConstants,
    DomainEdge,
    DomainGraph,
    DomainNode,
    RelationCandidate,
)
from core.domain.pipeline import (
    HesperiaPipelineRunner,
    export_metric_report_json,
    metric_report_to_dict,
    run_corpus,
    run_document,
    run_pipeline,
)


def _test_domain_graph() -> DomainGraph:
    """Small domain: A, B, C with triangle edges."""
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


def _test_constants() -> DomainConstants:
    return DomainConstants(
        domain_node_count=100,
        domain_degree_p95=10.0,
        domain_distance_p95=5.0,
    )


def _test_document_input() -> DocumentInput:
    """One document: hits on A, B, C and relations A-B, B-C, A-C."""
    hits = [
        ConceptHit("A", 0),
        ConceptHit("B", 1),
        ConceptHit("C", 2),
        ConceptHit("A", 3),
    ]
    relations = [
        RelationCandidate("A", "B", "r"),
        RelationCandidate("B", "C", "r"),
        RelationCandidate("A", "C", "r"),
    ]
    return DocumentInput(source_id="paper_001", hits=hits, relations=relations)


def test_full_pipeline() -> None:
    """E2E: run_document → report has 6 primitives, 35 derived, 41 fingerprint values, non-null hash."""
    doc = _test_document_input()
    domain = _test_domain_graph()
    constants = _test_constants()

    report = run_document(
        domain,
        constants,
        doc.source_id,
        doc.hits,
        doc.relations,
        domain_release="test_v0_1",
    )

    assert len(report.primitive_map) == 6
    assert len(report.derived_map) == 35
    assert len(report.fingerprint.metric_values) == 41
    assert len(report.fingerprint.metric_names) == 41
    assert report.fingerprint.vector_hash is not None
    assert len(report.fingerprint.vector_hash) > 0
    assert report.source_id == "paper_001"


def test_run_pipeline_returns_fingerprint() -> None:
    """run_pipeline returns DomainFingerprint only."""
    doc = _test_document_input()
    fp = run_pipeline(
        _test_domain_graph(),
        _test_constants(),
        doc.source_id,
        doc.hits,
        doc.relations,
    )
    assert fp.metric_values is not None
    assert len(fp.metric_values) == 41
    assert fp.primitive_map is not None
    assert fp.derived_map is not None


def test_runner_class() -> None:
    """HesperiaPipelineRunner.run_document produces same result as run_document()."""
    doc = _test_document_input()
    runner = HesperiaPipelineRunner(_test_domain_graph(), _test_constants())
    report = runner.run_document(doc.source_id, doc.hits, doc.relations)
    assert len(report.primitive_map) == 6
    assert len(report.derived_map) == 35
    assert report.fingerprint.vector_hash is not None


def test_metric_report_to_dict() -> None:
    """metric_report_to_dict is JSON-serializable and has sourceId, primitives, derived, fingerprint."""
    doc = _test_document_input()
    report = run_document(
        _test_domain_graph(),
        _test_constants(),
        doc.source_id,
        doc.hits,
        doc.relations,
    )
    d = metric_report_to_dict(report)
    assert "sourceId" in d
    assert d["sourceId"] == "paper_001"
    assert "primitives" in d
    assert "derived" in d
    assert "fingerprint" in d
    assert len(d["primitives"]) == 6
    assert len(d["derived"]) == 35
    assert d["fingerprint"]["fingerprintVersion"] is not None
    assert d["fingerprint"]["vectorHash"] is not None
    # Round-trip JSON
    s = json.dumps(d, sort_keys=True)
    loaded = json.loads(s)
    assert loaded["sourceId"] == d["sourceId"]
    assert len(loaded["fingerprint"]["metricValues"]) == 41


def test_export_metric_report_json() -> None:
    """export_metric_report_json writes deterministic JSON file."""
    doc = _test_document_input()
    report = run_document(
        _test_domain_graph(),
        _test_constants(),
        doc.source_id,
        doc.hits,
        doc.relations,
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    try:
        export_metric_report_json(path, report)
        content = Path(path).read_text()
        loaded = json.loads(content)
        assert loaded["sourceId"] == report.source_id
        assert "primitives" in loaded and "derived" in loaded and "fingerprint" in loaded
        assert len(loaded["fingerprint"]["metricValues"]) == 41
    finally:
        Path(path).unlink(missing_ok=True)


def test_batch_runner() -> None:
    """run_corpus returns one MetricReport per DocumentInput."""
    domain = _test_domain_graph()
    constants = _test_constants()
    docs = [
        DocumentInput(
            source_id="doc_1",
            hits=[ConceptHit("A", 0), ConceptHit("B", 1)],
            relations=[RelationCandidate("A", "B", "r")],
        ),
        DocumentInput(
            source_id="doc_2",
            hits=[ConceptHit("C", 0)],
            relations=[],
        ),
    ]
    results = run_corpus(docs, domain, constants)
    assert len(results) == 2
    assert results[0].source_id == "doc_1"
    assert results[1].source_id == "doc_2"
    assert len(results[0].fingerprint.metric_values) == 41
    assert len(results[1].fingerprint.metric_values) == 41


def test_determinism_same_input_same_hash() -> None:
    """Same document input → same fingerprint hash and metric values."""
    doc = _test_document_input()
    domain = _test_domain_graph()
    constants = _test_constants()
    r1 = run_document(domain, constants, doc.source_id, doc.hits, doc.relations)
    r2 = run_document(domain, constants, doc.source_id, doc.hits, doc.relations)
    assert r1.fingerprint.vector_hash == r2.fingerprint.vector_hash
    assert r1.fingerprint.metric_values == r2.fingerprint.metric_values
