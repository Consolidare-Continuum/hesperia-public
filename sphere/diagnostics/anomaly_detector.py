# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Structural anomaly detector.
Detects deviation from expected bounded behavior. Machine-clean diagnostics only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SPEC = _REPO_ROOT / "spec" / "diagnostic_rules.yaml"

ALLOWED_SEVERITIES = frozenset({"low", "medium", "high", "critical"})


def _load_config(config: dict[str, Any]) -> dict[str, Any]:
    """Merge spec thresholds into config. Fallback defaults if spec missing."""
    out = dict(config)
    if (config.get("diagnostic_rules_path") or _DEFAULT_SPEC) and Path(config.get("diagnostic_rules_path") or _DEFAULT_SPEC).exists():
        path = Path(config.get("diagnostic_rules_path") or _DEFAULT_SPEC)
        with open(path, encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        if spec and "anomaly" in spec:
            out.setdefault("anomaly", spec["anomaly"])
    if "anomaly" not in out:
        out["anomaly"] = {
            "enabled": True,
            "zero_signal_enabled": True,
            "ultra_sparse_coverage_threshold": 0.02,
            "excessive_jump_threshold": 0.60,
            "transition_concentration_threshold": 0.75,
            "metric_bounds_check_enabled": True,
        }
    return out


def _jump_rate_value(metrics: dict[str, Any]) -> float:
    """Extract jump_rate as scalar."""
    v = metrics.get("jump_rate")
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict) and "jump_rate" in v:
        return float(v["jump_rate"])
    return 0.0


def detect_structural_anomalies(metrics: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Detect structural anomalies from metrics. Returns list of canonical diagnostic objects.
    v1 anomaly classes: zero-structure, ultra-sparse, excessive jump, transition concentration, metric-out-of-bounds.
    """
    cfg = _load_config(config)
    anomaly_cfg = cfg.get("anomaly", {})
    if not anomaly_cfg.get("enabled", True):
        return []

    # Shape validation (raise only for malformed types/shapes)
    area_vector = metrics.get("area_vector")
    family_counts = metrics.get("family_counts")
    transition_matrix = metrics.get("transition_matrix")
    if area_vector is not None and (not isinstance(area_vector, (list, tuple)) or len(area_vector) != 12):
        raise ValueError("area_vector must be length 12 when provided")
    if family_counts is not None and (not isinstance(family_counts, (list, tuple)) or len(family_counts) != 288):
        raise ValueError("family_counts must be length 288 when provided")
    if transition_matrix is not None:
        if not isinstance(transition_matrix, (list, tuple)) or len(transition_matrix) != 12:
            raise ValueError("transition_matrix must be 12x12 when provided")
        for row in transition_matrix or []:
            if not isinstance(row, (list, tuple)) or len(row) != 12:
                raise ValueError("transition_matrix must be 12x12 when provided")

    diagnostics: list[dict[str, Any]] = []
    fc = family_counts or []
    fc_sum = sum(fc) if isinstance(fc, (list, tuple)) else 0
    coverage = float(metrics.get("coverage", 0.0))
    jump_rate = _jump_rate_value(metrics)
    stability_index = float(metrics.get("stability_index", 0.0))
    loopability = float(metrics.get("loopability", 0.0))

    # Zero structure
    if anomaly_cfg.get("zero_signal_enabled", True) and fc_sum == 0:
        diagnostics.append({
            "diagnostic_code": "STRUCTURAL_ANOMALY_ZERO_SIGNAL",
            "severity": "high",
            "message": "No structural mass detected.",
            "evidence": {"family_counts_sum": 0},
            "source_detector": "anomaly_detector",
        })

    # Ultra-sparse
    thresh = float(anomaly_cfg.get("ultra_sparse_coverage_threshold", 0.02))
    if fc_sum > 0 and coverage < thresh:
        diagnostics.append({
            "diagnostic_code": "STRUCTURAL_ANOMALY_ULTRA_SPARSE",
            "severity": "high",
            "message": "Structural coverage extremely low.",
            "evidence": {"coverage": coverage, "family_counts_sum": fc_sum},
            "source_detector": "anomaly_detector",
        })

    # Excessive jump
    thresh = float(anomaly_cfg.get("excessive_jump_threshold", 0.60))
    if jump_rate > thresh:
        diagnostics.append({
            "diagnostic_code": "STRUCTURAL_ANOMALY_EXCESSIVE_JUMP",
            "severity": "high",
            "message": "Jump rate exceeds threshold.",
            "evidence": {"jump_rate": jump_rate},
            "source_detector": "anomaly_detector",
        })

    # Transition concentration
    trans = transition_matrix if isinstance(transition_matrix, (list, tuple)) else []
    if trans:
        total = sum(c for row in trans for c in (row if isinstance(row, (list, tuple)) else []))
        if total > 0:
            flat = [c for row in trans for c in (row if isinstance(row, (list, tuple)) else [])]
            max_c = max(flat) if flat else 0
            thresh = float(anomaly_cfg.get("transition_concentration_threshold", 0.75))
            if max_c / total > thresh:
                diagnostics.append({
                    "diagnostic_code": "STRUCTURAL_ANOMALY_TRANSITION_CONCENTRATION",
                    "severity": "medium",
                    "message": "One transition dominates excessively.",
                    "evidence": {"max_transition_ratio": max_c / total, "total_transitions": total},
                    "source_detector": "anomaly_detector",
                })

    # Metric out-of-bounds
    if anomaly_cfg.get("metric_bounds_check_enabled", True):
        if not (0 <= coverage <= 1):
            diagnostics.append({
                "diagnostic_code": "STRUCTURAL_ANOMALY_METRIC_OUT_OF_BOUNDS",
                "severity": "high",
                "message": "Coverage not in [0,1].",
                "evidence": {"coverage": coverage},
                "source_detector": "anomaly_detector",
            })
        if not (0 <= jump_rate <= 1):
            diagnostics.append({
                "diagnostic_code": "STRUCTURAL_ANOMALY_METRIC_OUT_OF_BOUNDS",
                "severity": "high",
                "message": "Jump rate not in [0,1].",
                "evidence": {"jump_rate": jump_rate},
                "source_detector": "anomaly_detector",
            })
        if not (0 <= stability_index <= 1):
            diagnostics.append({
                "diagnostic_code": "STRUCTURAL_ANOMALY_METRIC_OUT_OF_BOUNDS",
                "severity": "high",
                "message": "Stability index not in [0,1].",
                "evidence": {"stability_index": stability_index},
                "source_detector": "anomaly_detector",
            })
        if not (0 <= loopability <= 1):
            diagnostics.append({
                "diagnostic_code": "STRUCTURAL_ANOMALY_METRIC_OUT_OF_BOUNDS",
                "severity": "high",
                "message": "Loopability not in [0,1].",
                "evidence": {"loopability": loopability},
                "source_detector": "anomaly_detector",
            })

    return diagnostics
