# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""Kolmogorov Semantic Inspection (KSI) v0.1 — Phi_e + Expected/residual pipeline."""

from .bridge import (
    BridgeSessionState,
    ConceptStructure,
    compute_bridge_need,
    classify_missing_bridge,
    gap,
    missing_bridge_incident_payload,
)
from .bundle import KsiBundleBlock, KsiConceptMetrics, empty_ksi_block
from .expected_j import (
    IncomingEdge,
    KsiThresholds,
    classify_concept_incident,
    compute_expected_area,
    compute_expected_j,
    compute_residual,
    is_dead_concept,
    is_over_activated,
    is_under_explained_activation,
    load_ksi_config,
)
from .flags import (
    ksi_enabled,
    ksi_phi_trace_enabled,
    ksi_sandbox_fixtures_enabled,
    phi_trace_enabled,
    teacher_inspect_only,
    teacher_packet_enabled,
)
from .gate import GateVerdict, validate_proposal, validate_proposal_packet
from .mirror import (
    MirrorCauseCandidate,
    classify_mirror_deficit_incident,
    compute_mirror_cause_scores,
    compute_mirror_deficit,
)
from .phi_e import PhiEParams, phi_e, phi_e_raw, phi_e_trace, r_e_for_type, sat
from .pipeline import (
    attach_ksi_to_engine_result,
    attach_ksi_to_extended,
    build_ksi_analyze_block,
    run_ksi_inspect,
    run_ksi_inspect_from_engine,
)
from .sandbox import replay_concept_residuals, sandbox_residual_improved
from .teacher import (
    TEACHER_RELATIONS_TEMPLATE,
    TEACHER_STRUCTURE_TEMPLATE,
    build_teacher_prompt_sections,
    rank_missing_bridges,
    serialize_teacher_packet,
)

__all__ = [
    "BridgeSessionState",
    "ConceptStructure",
    "GateVerdict",
    "IncomingEdge",
    "KsiBundleBlock",
    "KsiConceptMetrics",
    "KsiThresholds",
    "MirrorCauseCandidate",
    "PhiEParams",
    "TEACHER_RELATIONS_TEMPLATE",
    "TEACHER_STRUCTURE_TEMPLATE",
    "attach_ksi_to_engine_result",
    "attach_ksi_to_extended",
    "build_ksi_analyze_block",
    "build_teacher_prompt_sections",
    "classify_concept_incident",
    "classify_mirror_deficit_incident",
    "classify_missing_bridge",
    "compute_bridge_need",
    "compute_expected_area",
    "compute_expected_j",
    "compute_mirror_cause_scores",
    "compute_mirror_deficit",
    "compute_residual",
    "empty_ksi_block",
    "gap",
    "is_dead_concept",
    "is_over_activated",
    "is_under_explained_activation",
    "ksi_enabled",
    "ksi_phi_trace_enabled",
    "ksi_sandbox_fixtures_enabled",
    "load_ksi_config",
    "missing_bridge_incident_payload",
    "phi_e",
    "phi_e_raw",
    "phi_e_trace",
    "phi_trace_enabled",
    "rank_missing_bridges",
    "replay_concept_residuals",
    "r_e_for_type",
    "run_ksi_inspect",
    "run_ksi_inspect_from_engine",
    "sandbox_residual_improved",
    "sat",
    "serialize_teacher_packet",
    "teacher_inspect_only",
    "teacher_packet_enabled",
    "validate_proposal",
    "validate_proposal_packet",
]
