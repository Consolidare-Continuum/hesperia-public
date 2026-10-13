# HESPERIA — RAD. Semantic field dynamics (Ethan spec), phased implementation.
# Keep package exports lazy so shipping/runtime imports do not eagerly pull non-shipping modules.

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "matrix_builders",
    "SemanticFieldParams",
    "FieldStepResult",
    "TimelineStep",
    "RunUntilConvergenceOutcome",
    "EnergyControlParams",
    "build_family_laplacian",
    "build_resistance_matrix",
    "build_contradiction_matrix",
    "step_field",
    "compute_energy",
    "run_until_convergence",
    "aggregate_family_to_area",
    "build_identity_family_mapping",
    "CalibrationCandidate",
    "compute_hspr_calibration_index",
    "generate_candidate_grid",
    "evaluate_candidate",
    "calibrate_parameter_grid",
    "FieldDynamicsState",
    "Phase1Theta",
    "Phase2Theta",
    "Phase3Theta",
    "Phase4Theta",
    "field_dynamics_enabled",
    "field_dynamics_phase2_enabled",
    "field_dynamics_phase3_enabled",
    "field_dynamics_phase4_enabled",
    "step_phase1",
    "step_phase2",
    "step_phase3",
    "apply_xi_to_contradiction_signal",
    "field_dynamics_xi_enabled",
    "field_dynamics_xi_kme_enabled",
    "xi_proxy_from_kme_active_graph",
    "xi_proxy_from_triz_rows",
    "SEMANTIC_FIELD_EQUATIONS_SPEC_ID",
    "SemanticFieldParamsV1",
    "load_production_matrices",
    "build_default_matrices",
    "build_stub_matrices_dev_only",
    "semantic_field_e2e_bundle",
    "step_field_euler",
]

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "matrix_builders": ("hesperia.extensions.dynamics", "matrix_builders"),
    "CalibrationCandidate": ("hesperia.extensions.dynamics.calibration", "CalibrationCandidate"),
    "calibrate_parameter_grid": ("hesperia.extensions.dynamics.calibration", "calibrate_parameter_grid"),
    "compute_hspr_calibration_index": ("hesperia.extensions.dynamics.calibration", "compute_hspr_calibration_index"),
    "evaluate_candidate": ("hesperia.extensions.dynamics.calibration", "evaluate_candidate"),
    "generate_candidate_grid": ("hesperia.extensions.dynamics.calibration", "generate_candidate_grid"),
    "EnergyControlParams": ("hesperia.extensions.dynamics.equations", "EnergyControlParams"),
    "FieldStepResult": ("hesperia.extensions.dynamics.equations", "FieldStepResult"),
    "RunUntilConvergenceOutcome": ("hesperia.extensions.dynamics.equations", "RunUntilConvergenceOutcome"),
    "SemanticFieldParams": ("hesperia.extensions.dynamics.equations", "SemanticFieldParams"),
    "TimelineStep": ("hesperia.extensions.dynamics.equations", "TimelineStep"),
    "aggregate_family_to_area": ("hesperia.extensions.dynamics.equations", "aggregate_family_to_area"),
    "build_contradiction_matrix": ("hesperia.extensions.dynamics.equations", "build_contradiction_matrix"),
    "build_family_laplacian": ("hesperia.extensions.dynamics.equations", "build_family_laplacian"),
    "build_identity_family_mapping": ("hesperia.extensions.dynamics.equations", "build_identity_family_mapping"),
    "build_resistance_matrix": ("hesperia.extensions.dynamics.equations", "build_resistance_matrix"),
    "compute_energy": ("hesperia.extensions.dynamics.equations", "compute_energy"),
    "run_until_convergence": ("hesperia.extensions.dynamics.equations", "run_until_convergence"),
    "step_field": ("hesperia.extensions.dynamics.equations", "step_field"),
    "field_dynamics_enabled": ("hesperia.extensions.dynamics.phase1", "field_dynamics_enabled"),
    "step_phase1": ("hesperia.extensions.dynamics.phase1", "step_phase1"),
    "field_dynamics_phase2_enabled": ("hesperia.extensions.dynamics.phase2", "field_dynamics_phase2_enabled"),
    "step_phase2": ("hesperia.extensions.dynamics.phase2", "step_phase2"),
    "field_dynamics_phase3_enabled": ("hesperia.extensions.dynamics.phase3", "field_dynamics_phase3_enabled"),
    "step_phase3": ("hesperia.extensions.dynamics.phase3", "step_phase3"),
    "field_dynamics_phase4_enabled": ("hesperia.extensions.dynamics.phase4", "field_dynamics_phase4_enabled"),
    "apply_xi_to_contradiction_signal": ("hesperia.extensions.dynamics.xi_proxy", "apply_xi_to_contradiction_signal"),
    "field_dynamics_xi_enabled": ("hesperia.extensions.dynamics.xi_proxy", "field_dynamics_xi_enabled"),
    "field_dynamics_xi_kme_enabled": ("hesperia.extensions.dynamics.xi_proxy", "field_dynamics_xi_kme_enabled"),
    "xi_proxy_from_kme_active_graph": ("hesperia.extensions.dynamics.xi_proxy", "xi_proxy_from_kme_active_graph"),
    "xi_proxy_from_triz_rows": ("hesperia.extensions.dynamics.xi_proxy", "xi_proxy_from_triz_rows"),
    "SEMANTIC_FIELD_EQUATIONS_SPEC_ID": ("hesperia.extensions.dynamics.semantic_field_v1", "SPEC_ID"),
    "SemanticFieldParamsV1": ("hesperia.extensions.dynamics.semantic_field_v1", "SemanticFieldParamsV1"),
    "build_default_matrices": ("hesperia.extensions.dynamics.semantic_field_v1", "build_default_matrices"),
    "build_stub_matrices_dev_only": ("hesperia.extensions.dynamics.semantic_field_v1", "build_stub_matrices_dev_only"),
    "load_semantic_field_params_v1": ("hesperia.extensions.dynamics.semantic_field_v1", "load_semantic_field_params_v1"),
    "semantic_field_e2e_bundle": ("hesperia.extensions.dynamics.semantic_field_v1", "semantic_field_e2e_bundle"),
    "step_field_euler": ("hesperia.extensions.dynamics.semantic_field_v1", "step_field_euler"),
    "FieldDynamicsState": ("hesperia.extensions.dynamics.state", "FieldDynamicsState"),
    "Phase1Theta": ("hesperia.extensions.dynamics.state", "Phase1Theta"),
    "Phase2Theta": ("hesperia.extensions.dynamics.state", "Phase2Theta"),
    "Phase3Theta": ("hesperia.extensions.dynamics.state", "Phase3Theta"),
    "Phase4Theta": ("hesperia.extensions.dynamics.state", "Phase4Theta"),
    "load_production_matrices": ("core.engine.matrix_loader", "load_production_matrices"),
}


def __getattr__(name: str) -> Any:
    if name == "matrix_builders":
        return import_module("hesperia.extensions.dynamics.matrix_builders")
    target = _EXPORT_MAP.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr_name = target
    module = import_module(module_name)
    return getattr(module, attr_name)
