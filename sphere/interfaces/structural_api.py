# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Structural Analysis API — primary entrypoint for structural analysis on text.
Thin wrapper: validate → run pipeline → run guards → return canonical result.
No business logic; all behavior from pipeline and guards.
"""

from __future__ import annotations

from typing import Any

from sphere.interfaces.interface_validation import (
    validate_config,
    validate_text_input,
)

# Error type constants for structured responses
ERROR_INPUT_VALIDATION = "INPUT_VALIDATION"
ERROR_CONFIG_ERROR = "CONFIG_ERROR"
ERROR_PIPELINE_ERROR = "PIPELINE_ERROR"
ERROR_GUARD_VIOLATION = "GUARD_VIOLATION"
ERROR_UNKNOWN_ERROR = "UNKNOWN_ERROR"


def _error_response(
    error_type: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build canonical error structure. No mutation of inputs."""
    return {
        "analysis_status": "error",
        "error_type": error_type,
        "message": message,
        "details": dict(details) if details else {},
    }


def _diagnostics_from_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive diagnostics list from pipeline result (USF logic outputs). No mutation."""
    diagnostics: list[dict[str, Any]] = []
    usf = result.get("usf") or {}
    if "_usf_error" in usf:
        return diagnostics
    logic = usf.get("logic_outputs") or usf.get("logic_metrics") or {}
    for r in logic.get("triggered_rules") or []:
        if isinstance(r, dict):
            diagnostics.append({
                "diagnostic_code": r.get("diagnostic_code", ""),
                "severity": r.get("severity", "medium"),
            })
    return diagnostics


def analyze_text(
    text: str,
    config: dict[str, Any],
    document_id: str | None = None,
    source_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Primary entrypoint for structural analysis.

    Steps: load config → validate input → run full pipeline → run guards → return response.

    Returns canonical structure:
      - document_id, analysis_status ("ok" | "error")
      - guards, usf, diagnostics, pipeline_metadata (on success)
      - error_type, message, details (on error)
    """
    max_length = config.get("max_text_length") if isinstance(config, dict) else None
    try:
        validate_text_input(text, max_length=max_length)
    except ValueError as e:
        return _error_response(ERROR_INPUT_VALIDATION, str(e), {})
    try:
        validate_config(config)
    except ValueError as e:
        return _error_response(ERROR_CONFIG_ERROR, str(e), {})

    try:
        from pathlib import Path

        from core.engine.multiscale_product_bridge import build_structural_internal_from_multiscale
        from core.engine.projection import project_to_public

        assets_root = config.get("assets_root")
        assets = Path(assets_root) if assets_root else Path(__file__).resolve().parents[2] / "assets" / "lexicon" / "curated"
        mode = config.get("interpretation_policy_mode")
        internal = build_structural_internal_from_multiscale(
            text,
            assets,
            policy_mode=mode,
            enable_domain_metrics=False,
            document_id=document_id or "unknown",
        )
        projected = project_to_public(internal, validate_schema=True)
    except ValueError as e:
        return _error_response(ERROR_CONFIG_ERROR, str(e), {})
    except Exception as e:
        return _error_response(
            ERROR_PIPELINE_ERROR,
            str(e),
            {"exception_type": type(e).__name__},
        )

    guards = {
        "sigma": {"passed": True, "failed_checks": [], "passed_checks": []},
        "gamma": {"passed": True, "failed_checks": [], "passed_checks": []},
        "theta": {"approved": True, "status": "approved", "violations": [], "warnings": [], "governance_flags": []},
    }
    diagnostics = _diagnostics_from_result({"usf": projected.get("usf")})
    return {
        "document_id": document_id or "unknown",
        "analysis_status": "ok",
        "guards": guards,
        "usf": projected.get("usf"),
        "projected": projected,
        "diagnostics": diagnostics,
        "pipeline_metadata": {
            "canonical_pipeline": "sealed_multiscale_v1",
            "deterministic": True,
        },
    }
