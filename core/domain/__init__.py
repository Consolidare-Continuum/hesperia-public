# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Domain metrics canonical entry point.
Compatibility shims remain under ``hesperia.engine.kme`` for older imports.
"""

from core.domain.active_graph import build_active_graph
from core.domain.derived_metrics import (
    compute,
    compute_derived_metrics,
    full_fingerprint,
    to_derived_vector,
    to_full_fingerprint,
    vector,
    zero_derived_metrics,
)
from core.domain.extractor import extract_constants
from core.domain.fingerprint import (
    MARKETABLE_DERIVED_ORDER,
    build_fingerprint,
    cosine_similarity,
    euclidean_distance,
    fingerprint_cosine,
    fingerprint_euclidean,
    fingerprint_manhattan,
    manhattan_distance,
    marketable_derived_from_map,
    same_fingerprint,
)
from core.domain.loader import load_domain_graph_from_json, load_frozen_constants
from core.domain.models import (
    ActiveEdge,
    ActiveGraph,
    ActiveNode,
    ConceptHit,
    DerivedMetrics,
    DocumentInput,
    DomainConstants,
    DomainEdge,
    DomainFingerprint,
    DomainGraph,
    DomainNode,
    DomainProfile,
    MetricReport,
    PrimitiveMetrics,
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
from core.domain.primitive_metrics import compute_primitives
from core.domain.profile import build_profile, classify_document, domain_distance

__all__ = [
    "ActiveEdge",
    "ActiveGraph",
    "ActiveNode",
    "ConceptHit",
    "DerivedMetrics",
    "DocumentInput",
    "DomainConstants",
    "DomainEdge",
    "DomainFingerprint",
    "DomainGraph",
    "DomainNode",
    "DomainProfile",
    "export_metric_report_json",
    "HesperiaPipelineRunner",
    "MetricReport",
    "metric_report_to_dict",
    "PrimitiveMetrics",
    "RelationCandidate",
    "domain_distance",
    "run_corpus",
    "run_document",
    "run_pipeline",
    "build_active_graph",
    "build_profile",
    "build_fingerprint",
    "classify_document",
    "compute",
    "compute_derived_metrics",
    "compute_primitives",
    "cosine_similarity",
    "euclidean_distance",
    "extract_constants",
    "fingerprint_cosine",
    "fingerprint_euclidean",
    "fingerprint_manhattan",
    "full_fingerprint",
    "load_domain_graph_from_json",
    "load_frozen_constants",
    "MARKETABLE_DERIVED_ORDER",
    "manhattan_distance",
    "marketable_derived_from_map",
    "same_fingerprint",
    "to_derived_vector",
    "to_full_fingerprint",
    "vector",
    "zero_derived_metrics",
]
