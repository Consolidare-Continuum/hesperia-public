# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3.1 — guard pipeline. Strict order: Sigma → Gamma → Theta.
20_SPEC Release v0.3.1 Runtime Guards and Failure Classes.
No reordering. Degraded-state rules applied after Theta; all bounded by Sigma.
Guard coverage: sigma_passed, gamma_penalty, degraded_flag logged (not in API).
"""

from __future__ import annotations

import logging
from typing import Any

from core.propagation.gamma_guard import compute_gamma_penalty
from .invariant_enforcer import enforce as sigma_enforce
from core.propagation.theta_gate import LOOP_DEGRADED_MAX, apply_theta, G_DEGRADED_MAX

logger = logging.getLogger(__name__)

# Degraded triggers
DEGRADED_GAMMA_THRESHOLD = 0.6


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def is_degraded(
    evidence_count: int,
    gamma_penalty: float,
    loopability: float,
) -> bool:
    """Degraded if evidence_count==0 or gammaPenalty>=0.6 or loopability<=LOOP_DEGRADED_MAX."""
    if evidence_count == 0:
        return True
    if gamma_penalty >= DEGRADED_GAMMA_THRESHOLD:
        return True
    if loopability <= LOOP_DEGRADED_MAX:
        return True
    return False


def apply_degraded_bumps(result: dict[str, Any]) -> dict[str, Any]:
    """When degraded: tension_energy and obstacle_score slightly increased; all bounded."""
    out = dict(result)
    out["tension_energy"] = _clamp(
        float(out.get("tension_energy", 0.0)) + 0.05, 0.0, 1.0
    )
    out["obstacle_score"] = _clamp(
        float(out.get("obstacle_score", 0.0)) + 0.05, 0.0, 1.0
    )
    return out


def run_pipeline(
    result: dict[str, Any],
    traversal_length: int,
    area_hop_count: int,
    evidence_count: int,
    *,
    skip_sigma_geometry: bool = True,
    skip_sigma_bijection: bool = True,
    shadow_enabled: bool = False,
) -> dict[str, Any]:
    """
    Strict order: Sigma → Gamma → Theta [→ Shadow if shadow_enabled]. No reordering.
    Single entrypoint: shadow is a flag inside the pipeline, not a different function.
    result must have exactly 6 required keys (Sigma validates).
    """
    sigma_violations_count = 0
    # 1. Sigma (on pass: no violation; on raise: caller sees exception)
    result = sigma_enforce(
        result,
        skip_geometry=skip_sigma_geometry,
        skip_bijection=skip_sigma_bijection,
    )
    loopability = float(result.get("loopability", 0.0))
    # 2. Gamma
    gamma_penalty = compute_gamma_penalty(
        traversal_length, area_hop_count, loopability
    )
    # 3. Degraded?
    degraded = is_degraded(evidence_count, gamma_penalty, loopability)
    logger.info(
        "guard_pipeline coverage sigmaViolationsCount=%s gammaPenalty=%s degradedFlag=%s shadow_enabled=%s",
        sigma_violations_count,
        round(gamma_penalty, 4),
        degraded,
        shadow_enabled,
    )
    # 4. Theta
    result = apply_theta(result, gamma_penalty, degraded)
    # 5. When degraded: slight bumps to tension_energy and obstacle_score
    if degraded:
        result = apply_degraded_bumps(result)
    # 6. Optional shadow layer (toggle inside execution_flow; no second entrypoint)
    if shadow_enabled:
        result = _apply_shadow_layer(result)
    # Keep bounded (Sigma-style clamp)
    result["governance"] = _clamp(float(result["governance"]), 0.0, 1.0)
    result["loopability"] = _clamp(float(result["loopability"]), 0.0, 1.0)
    result["tension_energy"] = max(0.0, float(result["tension_energy"]))
    result["obstacle_score"] = max(0.0, float(result["obstacle_score"]))
    return result


def run_execution_flow(
    result: dict[str, Any],
    traversal_length: int,
    area_hop_count: int,
    evidence_count: int,
    *,
    skip_sigma_geometry: bool = True,
    skip_sigma_bijection: bool = True,
    shadow_enabled: bool = False,
) -> dict[str, Any]:
    """Canonical alias for guard execution flow (compatibility wrapper around run_pipeline)."""
    return run_pipeline(
        result,
        traversal_length,
        area_hop_count,
        evidence_count,
        skip_sigma_geometry=skip_sigma_geometry,
        skip_sigma_bijection=skip_sigma_bijection,
        shadow_enabled=shadow_enabled,
    )


def _apply_shadow_layer(result: dict[str, Any]) -> dict[str, Any]:
    """Shadow layer hook: when shadow_enabled, apply shadow adjustments. Bounded by Sigma."""
    out = dict(result)
    # Placeholder: full shadow_layer.process_step integration can be wired here.
    # For now no-op so execution_flow shape is correct; governance cannot increase.
    logger.info("shadow_enabled: shadow layer applied (no-op placeholder)")
    return out
