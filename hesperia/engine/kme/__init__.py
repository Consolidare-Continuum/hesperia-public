# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA Knowledge Metrics Engine (KME).
Deterministic computation of structural knowledge metrics and fingerprints for documents and domains.
Compatibility facade over canonical implementations in core.domain.
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
from hesperia.extensions.triz.models import TRIZSignals
from hesperia.engine.kme.fingerprint_distance import (
    cosine_distance,
    wasserstein_distance,
    fingerprint_distance,
)
from hesperia.engine.kme.clinical_bridge import (
    load_domain_graph_from_dict_b,
    load_concept_relations,
    activation_to_hits_and_relations,
    build_clinical_active_graph,
    run_kme_from_activation,
    load_clinical_relation_sources,
    build_active_concept_nodes,
    build_active_family_nodes,
    build_active_area_nodes,
    build_hierarchical_edges,
    build_concept_relation_edges,
    build_family_topology_edges,
    build_area_topology_edges,
    build_clinical_active_graph_hierarchical,
    analyze_session_to_kme_graph,
    run_session_kme_pipeline,
    ACTIVATION_THRESHOLD,
    AREA_ACTIVE_THRESHOLD,
    TOP_K_CONCEPTS,
    TOP_K_FAMILIES,
    MIN_EDGE_WEIGHT,
    load_concept_relation_weights,
)

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
    "MetricReport",
    "PrimitiveMetrics",
    "RelationCandidate",
    "TRIZSignals",
    "build_active_graph",
    "build_fingerprint",
    "build_profile",
    "classify_document",
    "compute",
    "compute_derived_metrics",
    "compute_primitives",
    "cosine_similarity",
    "domain_distance",
    "euclidean_distance",
    "export_metric_report_json",
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
    "metric_report_to_dict",
    "run_corpus",
    "run_document",
    "run_pipeline",
    "same_fingerprint",
    "to_derived_vector",
    "to_full_fingerprint",
    "vector",
    "zero_derived_metrics",
    "HesperiaPipelineRunner",
    "load_domain_graph_from_dict_b",
    "load_concept_relations",
    "activation_to_hits_and_relations",
    "build_clinical_active_graph",
    "run_kme_from_activation",
    "load_clinical_relation_sources",
    "build_active_concept_nodes",
    "build_active_family_nodes",
    "build_active_area_nodes",
    "build_hierarchical_edges",
    "build_concept_relation_edges",
    "build_family_topology_edges",
    "build_area_topology_edges",
    "build_clinical_active_graph_hierarchical",
    "analyze_session_to_kme_graph",
    "run_session_kme_pipeline",
    "ACTIVATION_THRESHOLD",
    "AREA_ACTIVE_THRESHOLD",
    "TOP_K_CONCEPTS",
    "TOP_K_FAMILIES",
    "MIN_EDGE_WEIGHT",
    "load_concept_relation_weights",
    "cosine_distance",
    "wasserstein_distance",
    "fingerprint_distance",
]
