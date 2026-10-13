# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.
#
# HSPR Calibration Index (HCI) + grid search over semantic field parameters.
#
# Graduated to core 2026-07-31 (was hesperia/extensions/dynamics/calibration.py — pure
# numeric optimization, not domain-tied). The old location now re-exports from here for
# backward compatibility.

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Dict, List, Mapping, Sequence

import numpy as np

from core.math.field_dynamics import (
    SemanticFieldParams,
    aggregate_sources_with_params,
    build_contradiction_matrix,
    build_family_laplacian,
    build_resistance_matrix,
    compute_energy,
    compute_observables,
    run_until_convergence,
)


def _round(x: float, digits: int = 6) -> float:
    return round(float(x), digits)


@dataclass(frozen=True)
class CalibrationCandidate:
    alpha: float
    beta: float
    gamma: float
    delta: float
    mu: float
    dt: float

    def to_params(
        self,
        *,
        epsilon: float,
        tau: float,
        clip_mode: bool,
    ) -> SemanticFieldParams:
        return SemanticFieldParams(
            alpha=self.alpha,
            beta=self.beta,
            gamma=self.gamma,
            delta=self.delta,
            mu=self.mu,
            dt=self.dt,
            epsilon=epsilon,
            tau=tau,
            clip_mode=clip_mode,
        )

    def to_json_dict(self) -> Dict[str, float]:
        return {
            "alpha": _round(self.alpha),
            "beta": _round(self.beta),
            "gamma": _round(self.gamma),
            "delta": _round(self.delta),
            "mu": _round(self.mu),
            "dt": _round(self.dt),
        }


def _normalize_positive_benefit(x: float, kappa: float = 1.0) -> float:
    x = max(0.0, float(x))
    return x / (x + float(kappa))


def _normalize_positive_penalty(x: float) -> float:
    x = max(0.0, float(x))
    return 1.0 / (1.0 + x)


def compute_hspr_calibration_index(
    *,
    stability_score: float,
    source_alignment: float,
    energy_value: float,
    contradiction_load: float,
    diffusion_load: float,
    resistance_load: float,
    weights: Mapping[str, float] | None = None,
    source_alignment_kappa: float = 1.0,
) -> Dict[str, Any]:
    """
    HSPR Calibration Index (HCI), bounded in [0,1].

    Higher is better.
    """
    default_weights = {
        "stability": 0.25,
        "source_alignment": 0.25,
        "energy": 0.15,
        "contradiction": 0.15,
        "diffusion": 0.10,
        "resistance": 0.10,
    }
    w = dict(default_weights if weights is None else weights)

    required = {
        "stability",
        "source_alignment",
        "energy",
        "contradiction",
        "diffusion",
        "resistance",
    }
    if set(w.keys()) != required:
        raise ValueError(f"weights must have keys {sorted(required)}, got {sorted(w.keys())}")

    total_weight = sum(float(v) for v in w.values())
    if total_weight <= 0:
        raise ValueError("weights must sum to a positive value")
    w = {k: float(v) / total_weight for k, v in w.items()}

    comp_stability = min(max(float(stability_score), 0.0), 1.0)
    comp_source_alignment = _normalize_positive_benefit(source_alignment, kappa=source_alignment_kappa)
    comp_energy = _normalize_positive_penalty(max(float(energy_value), 0.0))
    comp_contradiction = _normalize_positive_penalty(contradiction_load)
    comp_diffusion = _normalize_positive_penalty(diffusion_load)
    comp_resistance = _normalize_positive_penalty(resistance_load)

    hci = (
        w["stability"] * comp_stability
        + w["source_alignment"] * comp_source_alignment
        + w["energy"] * comp_energy
        + w["contradiction"] * comp_contradiction
        + w["diffusion"] * comp_diffusion
        + w["resistance"] * comp_resistance
    )

    return {
        "hspr_calibration_index": float(hci),
        "components": {
            "stability": float(comp_stability),
            "source_alignment": float(comp_source_alignment),
            "energy": float(comp_energy),
            "contradiction": float(comp_contradiction),
            "diffusion": float(comp_diffusion),
            "resistance": float(comp_resistance),
        },
        "weights": w,
    }


def generate_candidate_grid(grid: Mapping[str, Sequence[float]]) -> List[CalibrationCandidate]:
    required = ["alpha", "beta", "gamma", "delta", "mu", "dt"]
    for key in required:
        if key not in grid:
            raise ValueError(f"grid missing required key: {key}")

    values = [grid[key] for key in required]
    candidates: List[CalibrationCandidate] = []

    for combo in product(*values):
        candidate = CalibrationCandidate(
            alpha=float(combo[0]),
            beta=float(combo[1]),
            gamma=float(combo[2]),
            delta=float(combo[3]),
            mu=float(combo[4]),
            dt=float(combo[5]),
        )
        candidates.append(candidate)

    return candidates


def evaluate_candidate(
    *,
    candidate: CalibrationCandidate,
    field_init: np.ndarray,
    adjacency_matrix: np.ndarray,
    resistance_vector: np.ndarray,
    contradiction_matrix: np.ndarray,
    documents: Sequence[Mapping[str, Any]],
    family_count: int,
    now_t: float | None,
    max_steps: int,
    epsilon: float,
    tau: float,
    clip_mode: bool,
    hci_weights: Mapping[str, float] | None = None,
    source_alignment_kappa: float = 1.0,
) -> Dict[str, Any]:
    params = candidate.to_params(epsilon=epsilon, tau=tau, clip_mode=clip_mode)
    laplacian = build_family_laplacian(adjacency_matrix)
    resistance = build_resistance_matrix(resistance_vector)
    contradiction = build_contradiction_matrix(contradiction_matrix)

    source_vector = aggregate_sources_with_params(
        documents,
        family_count=family_count,
        params=params,
        now_t=now_t,
    )

    f0 = np.asarray(field_init, dtype=float).ravel()
    if f0.shape[0] != family_count:
        raise ValueError(f"field_init length {f0.shape[0]} != family_count {family_count}")

    outcome = run_until_convergence(
        field_init=f0,
        source_t=source_vector,
        laplacian=laplacian,
        resistance_matrix=resistance,
        contradiction_matrix=contradiction,
        params=params,
        max_steps=max_steps,
    )
    field_final, timeline = outcome

    last_step = timeline[-1].result
    energy_final = compute_energy(
        field_t=field_final,
        source_t=source_vector,
        laplacian=laplacian,
        resistance_matrix=resistance,
        contradiction_matrix=contradiction,
        params=params,
    )

    observables = compute_observables(
        field_prev=last_step.field_prev,
        field_next=last_step.field_next,
        source_t=source_vector,
        laplacian=laplacian,
        resistance_matrix=resistance,
        contradiction_matrix=contradiction,
        params=params,
    )

    hci = compute_hspr_calibration_index(
        stability_score=observables["stability_score"],
        source_alignment=observables["source_alignment"],
        energy_value=energy_final,
        contradiction_load=observables["contradiction_load"],
        diffusion_load=observables["diffusion_load"],
        resistance_load=observables["resistance_load"],
        weights=hci_weights,
        source_alignment_kappa=source_alignment_kappa,
    )

    return {
        "candidate": candidate.to_json_dict(),
        "steps": len(timeline),
        "converged_numerical": bool(last_step.converged_numerical),
        "converged_contradiction": bool(last_step.converged_contradiction),
        "energy_final": _round(energy_final),
        "observables": {k: _round(v) for k, v in observables.items()},
        "hspr_calibration_index": _round(hci["hspr_calibration_index"]),
        "hspr_components": {k: _round(v) for k, v in hci["components"].items()},
        "hspr_weights": {k: _round(v) for k, v in hci["weights"].items()},
        "field_final": np.round(field_final, 6).tolist(),
        "source_vector": np.round(source_vector, 6).tolist(),
    }


def calibrate_parameter_grid(
    *,
    field_init: np.ndarray,
    adjacency_matrix: np.ndarray,
    resistance_vector: np.ndarray,
    contradiction_matrix: np.ndarray,
    documents: Sequence[Mapping[str, Any]],
    family_count: int,
    grid: Mapping[str, Sequence[float]],
    now_t: float | None = None,
    max_steps: int = 50,
    epsilon: float = 1e-6,
    tau: float = 1e-6,
    clip_mode: bool = True,
    hci_weights: Mapping[str, float] | None = None,
    source_alignment_kappa: float = 1.0,
    top_k: int = 10,
) -> Dict[str, Any]:
    candidates = generate_candidate_grid(grid)
    evaluations: List[Dict[str, Any]] = []

    for candidate in candidates:
        evaluation = evaluate_candidate(
            candidate=candidate,
            field_init=field_init,
            adjacency_matrix=adjacency_matrix,
            resistance_vector=resistance_vector,
            contradiction_matrix=contradiction_matrix,
            documents=documents,
            family_count=family_count,
            now_t=now_t,
            max_steps=max_steps,
            epsilon=epsilon,
            tau=tau,
            clip_mode=clip_mode,
            hci_weights=hci_weights,
            source_alignment_kappa=source_alignment_kappa,
        )
        evaluations.append(evaluation)

    evaluations.sort(
        key=lambda x: (
            x["hspr_calibration_index"],
            x["converged_numerical"],
            x["converged_contradiction"],
            -x["energy_final"],
        ),
        reverse=True,
    )

    best = evaluations[0] if evaluations else None
    return {
        "candidate_count": len(evaluations),
        "best": best,
        "top_k": evaluations[: max(1, top_k)],
        "all_results": evaluations,
    }


__all__ = [
    "CalibrationCandidate",
    "compute_hspr_calibration_index",
    "generate_candidate_grid",
    "evaluate_candidate",
    "calibrate_parameter_grid",
]
