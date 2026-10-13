# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Guard runtime: run Sigma, Gamma, Theta in sequence and return combined result.
Orchestration only; no policy logic here.
"""

from __future__ import annotations

from typing import Any

from . import sigma_validator, gamma_validator, theta_governance


def run_all_guards(
    artifacts: dict[str, Any],
    layer_outputs: dict[str, Any],
    runtime_metadata: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Run Sigma (static) → Gamma (dynamic) → Theta (governance).
    Returns guards dict with sigma, gamma, theta results.
    """
    # Ensure runtime_metadata has usf and area_sequence when available for Gamma
    if "usf" not in runtime_metadata and "usf" in artifacts:
        runtime_metadata = dict(runtime_metadata)
        runtime_metadata["usf"] = artifacts.get("usf")
    if "executed_layers" not in runtime_metadata and "pipeline_metadata" in artifacts:
        runtime_metadata = dict(runtime_metadata)
        runtime_metadata.setdefault(
            "executed_layers",
            artifacts.get("pipeline_metadata", {}).get("executed_layers", list(range(1, 11))),
        )
        runtime_metadata.setdefault(
            "isolation_validation_passed",
            artifacts.get("pipeline_metadata", {}).get("isolation_validation_passed", True),
        )
        runtime_metadata.setdefault(
            "deterministic",
            artifacts.get("pipeline_metadata", {}).get("deterministic", True),
        )

    sigma_result = sigma_validator.validate_sigma_invariants(artifacts, config)
    gamma_result = gamma_validator.validate_gamma_invariants(
        layer_outputs, runtime_metadata, config
    )
    theta_result = theta_governance.evaluate_theta_governance(
        artifacts, sigma_result, gamma_result, config
    )

    return {
        "sigma": sigma_result,
        "gamma": gamma_result,
        "theta": theta_result,
    }
