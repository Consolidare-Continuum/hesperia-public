# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.
#
# MOVED 2026-07-31: the real implementation now lives in core.math.field_dynamics —
# this module is a first-class dynamics extension of core, not the owner of this math.
# Re-exported for backward compatibility; existing imports from this path keep working.

from __future__ import annotations

from core.math.field_dynamics import (
    ArrayLike,
    EnergyControlParams,
    EnergyMode,
    FieldStepResult,
    RunUntilConvergenceOutcome,
    SemanticFieldParams,
    TimelineStep,
    aggregate_family_to_area,
    aggregate_sources_with_params,
    build_contradiction_matrix,
    build_family_laplacian,
    build_identity_family_mapping,
    build_resistance_matrix,
    build_source_vector,
    compute_convergence_metrics,
    compute_energy,
    compute_observables,
    compute_pressure_vector,
    run_until_convergence,
    step_field,
)

__all__ = [
    "SemanticFieldParams",
    "FieldStepResult",
    "TimelineStep",
    "RunUntilConvergenceOutcome",
    "EnergyControlParams",
    "build_family_laplacian",
    "build_resistance_matrix",
    "build_contradiction_matrix",
    "build_source_vector",
    "aggregate_sources_with_params",
    "compute_pressure_vector",
    "compute_energy",
    "compute_observables",
    "compute_convergence_metrics",
    "step_field",
    "run_until_convergence",
    "aggregate_family_to_area",
    "build_identity_family_mapping",
]
