# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""KAM (research) — Kolmogorov–Arnold–Moser-inspired semantic perturbation-stability lens.

Inspection only. Does **not** implement or claim the KAM theorem.
Flag-gated via ``HESPERIA_KAM_ENABLED`` (default off). Runs after KSI-Inspector +
Teacher inspect-only in the apply-gate stack.
"""

from sphere.kam.apply_gate import KamApplyGateLens, inspect_apply_gate
from sphere.kam.bounds import KamBounds, clear_bounds_cache, load_kam_bounds
from sphere.kam.critical_paths import extract_critical_paths, with_critical_paths
from sphere.kam.flags import kam_bounds_path, kam_enabled, kam_inspect_only
from sphere.kam.kam_score import (
    KamScoreResult,
    KamVerdict,
    compute_kam_semantic_score,
    verdict_from_score,
)
from sphere.kam.perturbation_battery import (
    ALL_PERTURBATION_IDS,
    BatteryResult,
    PerturbationRow,
    run_perturbation_battery,
)
from sphere.kam.pipeline import attach_kam_to_engine_result, run_kam_inspect
from sphere.kam.report import SCHEMA_ID, build_kam_report
from sphere.kam.sisr import SisrResult, compute_sisr, path_overlap
from sphere.kam.trajectory_fingerprint import (
    SemanticTrajectoryFingerprint,
    build_trajectory_fingerprint,
)

__all__ = [
    "ALL_PERTURBATION_IDS",
    "SCHEMA_ID",
    "BatteryResult",
    "KamApplyGateLens",
    "KamBounds",
    "KamScoreResult",
    "KamVerdict",
    "PerturbationRow",
    "SemanticTrajectoryFingerprint",
    "SisrResult",
    "attach_kam_to_engine_result",
    "build_kam_report",
    "build_trajectory_fingerprint",
    "clear_bounds_cache",
    "compute_kam_semantic_score",
    "compute_sisr",
    "extract_critical_paths",
    "inspect_apply_gate",
    "kam_bounds_path",
    "kam_enabled",
    "kam_inspect_only",
    "load_kam_bounds",
    "path_overlap",
    "run_kam_inspect",
    "run_perturbation_battery",
    "verdict_from_score",
    "with_critical_paths",
]
