# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

from .phi_e import PhiEParams, phi_e, r_e_for_type, sat

IncidentConceptType = Literal[
    "DEAD_CONCEPT",
    "OVER_ACTIVATED",
    "UNDER_EXPLAINED_ACTIVATION",
]


@dataclass(frozen=True, slots=True)
class IncomingEdge:
    """One directed semantic edge i → j for KSI forward expectation (§5)."""

    source: str
    target: str
    relation_type: str
    w_e: float
    q_e: float = 0.6
    s_e: float = 1.0
    c_e: float = 1.0
    p_e: float = 1.0
    d_e: float = 1.0
    k_e: float = 0.05


@dataclass(frozen=True, slots=True)
class KsiThresholds:
    tau: float = 0.25
    tau_active: float = 0.5
    tau_dead: float = 0.1
    tau_expected: float = 0.5
    tau_explain: float = 0.15
    tau_mirror: float = 0.4
    tau_bridge: float = 0.55
    tau_teacher: float = 0.65
    tau_sandbox_delta: float = 0.25

    @classmethod
    def from_config(cls, config: Mapping[str, object] | None = None) -> KsiThresholds:
        if not config:
            config = load_ksi_config()
        th = config.get("thresholds") or {}
        if not isinstance(th, dict):
            th = {}
        return cls(
            tau=float(th.get("tau", 0.25)),
            tau_active=float(th.get("tau_active", 0.5)),
            tau_dead=float(th.get("tau_dead", 0.1)),
            tau_expected=float(th.get("tau_expected", 0.5)),
            tau_explain=float(th.get("tau_explain", 0.15)),
            tau_mirror=float(th.get("tau_mirror", 0.4)),
            tau_bridge=float(th.get("tau_bridge", 0.55)),
            tau_teacher=float(th.get("tau_teacher", 0.65)),
            tau_sandbox_delta=float(th.get("tau_sandbox_delta", 0.25)),
        )


def default_ksi_config_path() -> Path:
    return Path(__file__).resolve().parents[3] / "assets" / "data" / "ksi" / "ksi_config_v01.json"


def load_ksi_config(path: Path | None = None) -> dict[str, object]:
    if path is None:
        path = default_ksi_config_path()
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


def _phi_for_edge(edge: IncomingEdge, a_i: float, coefficients: Mapping[str, float] | None) -> float:
    r_e = r_e_for_type(edge.relation_type, coefficients)
    params = PhiEParams(
        a_i=a_i,
        w_e=edge.w_e,
        r_e=r_e,
        q_e=edge.q_e,
        s_e=edge.s_e,
        c_e=edge.c_e,
        p_e=edge.p_e,
        d_e=edge.d_e,
        k_e=edge.k_e,
    )
    return phi_e(params)


def compute_expected_j(
    concept_id: str,
    incoming_edges: list[IncomingEdge],
    activations: Mapping[str, float],
    *,
    coefficients: Mapping[str, float] | None = None,
) -> float:
    """Forward Expected_j = sat(Σ Φ_e) over incoming edges (KSI §5)."""
    total = 0.0
    for edge in incoming_edges:
        if edge.target != concept_id:
            continue
        a_i = float(activations.get(edge.source, 0.0))
        total += _phi_for_edge(edge, a_i, coefficients)
    return sat(total)


def compute_expected_area(
    area_id: str,
    concept_primary_area: Mapping[str, str],
    expected_by_concept: Mapping[str, float],
) -> float:
    """Area roll-up: sat(Σ Expected_j) for concepts with primary_area = area_id (§5)."""
    total = 0.0
    for concept_id, expected in expected_by_concept.items():
        if concept_primary_area.get(concept_id) == area_id:
            total += float(expected)
    return sat(total)


def compute_residual(expected_j: float, observed_j: float) -> float:
    """Semantic residual R_j = Expected_j − Observed_j (KSI §7)."""
    return float(expected_j) - float(observed_j)


def is_dead_concept(
    expected_j: float,
    observed_j: float,
    thresholds: KsiThresholds | None = None,
) -> bool:
    th = thresholds or KsiThresholds.from_config()
    return expected_j >= th.tau_expected and observed_j <= th.tau_dead


def is_over_activated(
    expected_j: float,
    observed_j: float,
    thresholds: KsiThresholds | None = None,
) -> bool:
    th = thresholds or KsiThresholds.from_config()
    return observed_j >= th.tau_active and expected_j <= th.tau_explain


def is_under_explained_activation(
    expected_j: float,
    observed_j: float,
    residual_j: float,
    thresholds: KsiThresholds | None = None,
) -> bool:
    th = thresholds or KsiThresholds.from_config()
    return observed_j > 0 and expected_j > 0 and residual_j > th.tau


def classify_concept_incident(
    *,
    expected_j: float,
    observed_j: float,
    residual_j: float | None = None,
    thresholds: KsiThresholds | None = None,
) -> IncidentConceptType | None:
    residual = (
        float(residual_j)
        if residual_j is not None
        else compute_residual(expected_j, observed_j)
    )
    if is_dead_concept(expected_j, observed_j, thresholds):
        return "DEAD_CONCEPT"
    if is_over_activated(expected_j, observed_j, thresholds):
        return "OVER_ACTIVATED"
    if is_under_explained_activation(expected_j, observed_j, residual, thresholds):
        return "UNDER_EXPLAINED_ACTIVATION"
    return None
