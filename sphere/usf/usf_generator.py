# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
USF (Universal Structural Fingerprint) generator.
Assembles outputs from Layers 3–9 into a single canonical USF artifact.
Strict validation; deterministic field ordering.
"""

from __future__ import annotations

from typing import Any


def _check_list_length(lst: Any, expected: int, name: str) -> None:
    if not isinstance(lst, (list, tuple)) or len(lst) != expected:
        raise ValueError(f"{name} must be a list of length {expected}, got {type(lst).__name__} len={len(lst) if isinstance(lst, (list, tuple)) else 'N/A'}")


def _check_matrix_12x12(m: Any, name: str) -> None:
    if not isinstance(m, (list, tuple)) or len(m) != 12:
        raise ValueError(f"{name} must be 12x12 (list of 12 rows), got {len(m) if isinstance(m, (list, tuple)) else 'N/A'} rows")
    for i, row in enumerate(m):
        if not isinstance(row, (list, tuple)) or len(row) != 12:
            raise ValueError(f"{name} row {i} must have length 12, got {len(row) if isinstance(row, (list, tuple)) else 'N/A'}")


def _build_logic_outputs(logic_outputs: dict[str, Any]) -> dict[str, Any]:
    """Build logic_outputs section; derive logic_flags from triggered_rules if empty."""
    triggered = list(logic_outputs["triggered_rules"])
    flags = list(logic_outputs.get("logic_flags") or [])
    if not flags and triggered:
        seen: set[str] = set()
        for r in triggered:
            if isinstance(r, dict) and r.get("diagnostic_code") and r["diagnostic_code"] not in seen:
                seen.add(r["diagnostic_code"])
                flags.append(r["diagnostic_code"])
    return {
        "triggered_rules": triggered,
        "logic_flags": flags,
        "structural_diagnostics": list(logic_outputs["structural_diagnostics"]),
    }


def _normalize_jump_rate(jump_rate: Any) -> float:
    """Accept scalar or Layer-6 style {jump_rate: float}; return float."""
    if isinstance(jump_rate, (int, float)):
        return float(jump_rate)
    if isinstance(jump_rate, dict) and "jump_rate" in jump_rate:
        return float(jump_rate["jump_rate"])
    return 0.0


def validate_usf_inputs(
    raw_metrics: dict[str, Any],
    dynamism_metrics: dict[str, Any],
    propagation_metrics: dict[str, Any],
    logic_outputs: dict[str, Any],
    provenance: dict[str, Any],
) -> None:
    """
    Validate required sections and core fields. Raises ValueError on contract violation.
    """
    # Raw metrics
    _check_list_length(raw_metrics.get("area_vector"), 12, "raw_metrics.area_vector")
    _check_list_length(raw_metrics.get("family_counts"), 288, "raw_metrics.family_counts")
    if "family_peaks" not in raw_metrics:
        raise ValueError("raw_metrics must include family_peaks")
    if not isinstance(raw_metrics.get("family_peaks"), (list, tuple)):
        raise ValueError("raw_metrics.family_peaks must be a list")
    for key in ("dominant_area", "dominant_family", "entropy", "tension", "loopability", "coverage"):
        if key not in raw_metrics:
            raise ValueError(f"raw_metrics must include {key}")

    # Dynamism
    if "transition_matrix" not in dynamism_metrics:
        raise ValueError("dynamism_metrics must include transition_matrix")
    _check_matrix_12x12(dynamism_metrics["transition_matrix"], "dynamism_metrics.transition_matrix")
    for key in ("trajectory", "curvature", "jump_rate", "stability_index"):
        if key not in dynamism_metrics:
            raise ValueError(f"dynamism_metrics must include {key}")

    # Propagation
    _check_list_length(propagation_metrics.get("propagated_area_vector"), 12, "propagation_metrics.propagated_area_vector")
    _check_list_length(propagation_metrics.get("propagated_family_counts"), 288, "propagation_metrics.propagated_family_counts")

    # Logic
    if "triggered_rules" not in logic_outputs or not isinstance(logic_outputs["triggered_rules"], (list, tuple)):
        raise ValueError("logic_outputs.triggered_rules must be a list")
    if "structural_diagnostics" not in logic_outputs or not isinstance(logic_outputs["structural_diagnostics"], (list, tuple)):
        raise ValueError("logic_outputs.structural_diagnostics must be a list")
    flags = logic_outputs.get("logic_flags")
    if flags is not None and not isinstance(flags, (list, tuple)):
        raise ValueError("logic_outputs.logic_flags must be a list when present")

    # Provenance
    for key in ("created_at", "pipeline_version", "input_hash", "deterministic"):
        if key not in provenance:
            raise ValueError(f"provenance must include {key}")
    if provenance.get("deterministic") is not True:
        raise ValueError("provenance.deterministic must be true for USF v1")


def build_usf_object(
    document_id: str,
    source_metadata: dict[str, Any],
    raw_metrics: dict[str, Any],
    dynamism_metrics: dict[str, Any],
    propagation_metrics: dict[str, Any],
    logic_outputs: dict[str, Any],
    provenance: dict[str, Any],
    usf_version: str = "1.0",
    interpretation_metrics: dict[str, Any] | None = None,
    shadow_metrics: dict[str, Any] | None = None,
    logic_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build canonical USF dict. When interpretation_metrics is provided, canonical
    structural meaning comes from it; logic_outputs remains for compatibility only.
    """
    jump_rate_val = _normalize_jump_rate(dynamism_metrics.get("jump_rate", 0.0))
    base: dict[str, Any] = {
        "usf_version": usf_version,
        "document_id": document_id,
        "source_metadata": dict(source_metadata),
        "raw_metrics": {
            "area_vector": list(raw_metrics["area_vector"]),
            "family_counts": list(raw_metrics["family_counts"]),
            "family_peaks": list(raw_metrics["family_peaks"]),
            "dominant_area": int(raw_metrics["dominant_area"]),
            "dominant_family": int(raw_metrics["dominant_family"]),
            "entropy": float(raw_metrics["entropy"]),
            "tension": float(raw_metrics["tension"]),
            "loopability": float(raw_metrics["loopability"]),
            "coverage": float(raw_metrics["coverage"]),
        },
        "dynamism_metrics": {
            "trajectory": dict(dynamism_metrics.get("trajectory", {})),
            "transition_matrix": [list(row) for row in dynamism_metrics["transition_matrix"]],
            "curvature": float(dynamism_metrics.get("curvature", 0.0)),
            "jump_rate": jump_rate_val,
            "stability_index": float(dynamism_metrics.get("stability_index", 0.0)),
        },
        "propagation_metrics": {
            "propagated_area_vector": list(propagation_metrics["propagated_area_vector"]),
            "propagated_family_counts": list(propagation_metrics["propagated_family_counts"]),
        },
        "logic_outputs": _build_logic_outputs(logic_outputs),
        "provenance": {
            "created_at": str(provenance["created_at"]),
            "pipeline_version": str(provenance["pipeline_version"]),
            "input_hash": str(provenance["input_hash"]),
            "deterministic": True,
        },
    }
    if interpretation_metrics:
        base["schema_version"] = usf_version
        base["dominant_area_id"] = interpretation_metrics.get("dominant_area_id")
        base["structural_state"] = interpretation_metrics.get("structural_state", "distributed_balanced")
        base["dominance_strength"] = interpretation_metrics.get("dominance_strength")
        base["entropy_state"] = interpretation_metrics.get("entropy_state", "stable")
        base["tension_state"] = interpretation_metrics.get("tension_state", "normal")
        base["propagation_state"] = interpretation_metrics.get("propagation_state", "minimal_spread")
        base["active_events"] = list(interpretation_metrics.get("active_events", []))
        base["interpretation_flags"] = list(interpretation_metrics.get("interpretation_flags", []))
        base["event_summary"] = dict(interpretation_metrics.get("event_summary", {}))
        base["diagnostics"] = dict(interpretation_metrics.get("interpretation_diagnostics", {}))
        base["fingerprint"] = {
            "structural_state": base["structural_state"],
            "dominant_area_id": base["dominant_area_id"],
            "active_events": base["active_events"],
            "interpretation_flags": base["interpretation_flags"],
        }
        base["compatibility"] = {
            "legacy_logic_outputs_present": bool(logic_outputs),
            "legacy_logic_bridge_used": False,
        }
    return base


def generate_usf(
    document_id: str,
    source_metadata: dict[str, Any],
    raw_metrics: dict[str, Any],
    dynamism_metrics: dict[str, Any],
    propagation_metrics: dict[str, Any],
    logic_outputs: dict[str, Any],
    provenance: dict[str, Any],
    usf_version: str = "1.0",
    interpretation_metrics: dict[str, Any] | None = None,
    shadow_metrics: dict[str, Any] | None = None,
    logic_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Assemble and validate a canonical USF artifact. When interpretation_metrics
    is provided, it is the canonical source for structural_state, active_events,
    interpretation_flags, etc.; logic_outputs is compatibility-only.
    """
    validate_usf_inputs(
        raw_metrics,
        dynamism_metrics,
        propagation_metrics,
        logic_outputs,
        provenance,
    )
    return build_usf_object(
        document_id=document_id,
        source_metadata=source_metadata,
        raw_metrics=raw_metrics,
        dynamism_metrics=dynamism_metrics,
        propagation_metrics=propagation_metrics,
        logic_outputs=logic_outputs,
        provenance=provenance,
        usf_version=usf_version,
        interpretation_metrics=interpretation_metrics,
        shadow_metrics=shadow_metrics,
        logic_metrics=logic_metrics,
    )
