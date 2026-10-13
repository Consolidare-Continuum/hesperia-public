# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from .expected_j import IncomingEdge, KsiThresholds
from .phi_e import r_e_for_type

MirrorIncidentType = Literal["MIRROR_DEFICIT"]


@dataclass(frozen=True, slots=True)
class MirrorCauseCandidate:
    source: str
    target: str
    cause_score: float


def compute_mirror_cause_scores(
    concept_id: str,
    incoming_edges: list[IncomingEdge],
    observed_j: float,
    *,
    coefficients: Mapping[str, float] | None = None,
) -> list[MirrorCauseCandidate]:
    """CauseScore(i->j) = A_j * W_e * R_e * Q_e * C_e * S_e (KSI section 6)."""
    a_j = float(observed_j)
    ranked: list[MirrorCauseCandidate] = []
    for edge in incoming_edges:
        if edge.target != concept_id:
            continue
        r_e = r_e_for_type(edge.relation_type, coefficients)
        score = a_j * edge.w_e * r_e * edge.q_e * edge.c_e * edge.s_e
        ranked.append(MirrorCauseCandidate(edge.source, edge.target, float(score)))
    ranked.sort(key=lambda row: row.cause_score, reverse=True)
    return ranked


def compute_mirror_deficit(
    observed_j: float,
    cause_scores: list[MirrorCauseCandidate],
    activations: Mapping[str, float],
    *,
    thresholds: KsiThresholds | None = None,
) -> float:
    th = thresholds or KsiThresholds.from_config()
    explained = 0.0
    for row in cause_scores:
        if float(activations.get(row.source, 0.0)) >= th.tau_active:
            explained += row.cause_score
    return float(observed_j) - explained


def classify_mirror_deficit_incident(
    *,
    observed_j: float,
    mirror_deficit: float,
    thresholds: KsiThresholds | None = None,
) -> MirrorIncidentType | None:
    th = thresholds or KsiThresholds.from_config()
    if observed_j >= th.tau_active and mirror_deficit > th.tau_mirror:
        return "MIRROR_DEFICIT"
    return None
