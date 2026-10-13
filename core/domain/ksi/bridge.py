# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

from .expected_j import KsiThresholds

MissingBridgeIncidentType = Literal["MISSING_BRIDGE"]


@dataclass(frozen=True, slots=True)
class ConceptStructure:
    primary_area: str = ""
    family: str = ""
    family_bias: str = ""


@dataclass(frozen=True, slots=True)
class BridgeSessionState:
    activations: Mapping[str, float]
    concept_structure: Mapping[str, ConceptStructure] = field(default_factory=dict)
    active_areas: frozenset[str] = frozenset()
    edge_strength: Mapping[tuple[str, str], float] = field(default_factory=dict)


def _co_activation(
    concept_i: str,
    concept_j: str,
    activations: Mapping[str, float],
    tau_active: float,
) -> float:
    a_i = float(activations.get(concept_i, 0.0))
    a_j = float(activations.get(concept_j, 0.0))
    return 1.0 if a_i >= tau_active and a_j >= tau_active else 0.0


def _context_match(
    concept_i: str,
    concept_j: str,
    session: BridgeSessionState,
) -> float:
    si = session.concept_structure.get(concept_i)
    sj = session.concept_structure.get(concept_j)
    if si and sj:
        if si.primary_area and si.primary_area == sj.primary_area:
            return 1.0
        if si.family and si.family == sj.family:
            return 1.0
    if session.active_areas and si and si.primary_area in session.active_areas:
        if sj and sj.primary_area in session.active_areas:
            return 1.0
    return 0.0


def _family_compatibility(
    concept_i: str,
    concept_j: str,
    session: BridgeSessionState,
) -> float:
    si = session.concept_structure.get(concept_i)
    sj = session.concept_structure.get(concept_j)
    if not si or not sj:
        return 0.0
    if si.primary_area and si.primary_area == sj.primary_area:
        return 1.0
    if si.family_bias and si.family_bias == sj.family_bias:
        return 1.0
    if si.family and si.family == sj.family:
        return 1.0
    return 0.0


def existing_relation_strength(
    concept_i: str,
    concept_j: str,
    session: BridgeSessionState,
) -> float:
    return float(session.edge_strength.get((concept_i, concept_j), 0.0))


def gap(concept_i: str, concept_j: str, session: BridgeSessionState) -> float:
    return 1.0 - existing_relation_strength(concept_i, concept_j, session)


def compute_bridge_need(
    concept_i: str,
    concept_j: str,
    session: BridgeSessionState,
    *,
    residual_j: float,
    thresholds: KsiThresholds | None = None,
) -> float:
    th = thresholds or KsiThresholds.from_config()
    co = _co_activation(concept_i, concept_j, session.activations, th.tau_active)
    ctx = _context_match(concept_i, concept_j, session)
    fam = _family_compatibility(concept_i, concept_j, session)
    g = gap(concept_i, concept_j, session)
    residual_term = max(0.0, float(residual_j))
    return co * ctx * fam * residual_term * g


def classify_missing_bridge(
    concept_i: str,
    concept_j: str,
    bridge_need: float,
    *,
    thresholds: KsiThresholds | None = None,
) -> MissingBridgeIncidentType | None:
    th = thresholds or KsiThresholds.from_config()
    if bridge_need >= th.tau_bridge:
        return "MISSING_BRIDGE"
    return None


def missing_bridge_incident_payload(
    concept_i: str,
    concept_j: str,
    bridge_need: float,
    session: BridgeSessionState,
) -> dict[str, Any]:
    return {
        "incident_type": "MISSING_BRIDGE",
        "source_concept_id": concept_i,
        "target_concept_id": concept_j,
        "concept_id": concept_j,
        "bridge_need_score": float(bridge_need),
        "existing_edge_strength": existing_relation_strength(concept_i, concept_j, session),
    }
