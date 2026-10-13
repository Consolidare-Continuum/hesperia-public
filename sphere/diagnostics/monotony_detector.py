# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Structural monotony detector.
Detects structurally narrow, repetitive, low-diversity discourse. Machine-clean diagnostics only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SPEC = _REPO_ROOT / "spec" / "diagnostic_rules.yaml"


def compute_dominant_area_share(area_vector: list[float] | tuple[float, ...]) -> float:
    """
    Share of mass in the dominant area: max(area_vector) / sum(area_vector).
    Returns 0.0 if sum is zero.
    """
    if not area_vector or len(area_vector) != 12:
        return 0.0
    total = sum(area_vector)
    if total <= 0:
        return 0.0
    return float(max(area_vector) / total)


def _load_config(config: dict[str, Any]) -> dict[str, Any]:
    out = dict(config)
    path = config.get("diagnostic_rules_path") or _DEFAULT_SPEC
    if path and Path(path).exists():
        with open(path, encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        if spec and "monotony" in spec:
            out.setdefault("monotony", spec["monotony"])
    if "monotony" not in out:
        out["monotony"] = {
            "enabled": True,
            "entropy_threshold": 0.35,
            "coverage_threshold": 0.20,
            "dominant_area_share_threshold": 0.65,
            "stability_high_threshold": 0.70,
            "unique_areas_max": 2,
        }
    return out


def detect_structural_monotony(metrics: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Detect structural monotony from metrics. Returns list of canonical diagnostic objects.
    v1: entropy < threshold; strengthened: entropy and coverage low; optional: dominant share, stability, unique areas.
    """
    cfg = _load_config(config)
    mono_cfg = cfg.get("monotony", {})
    if not mono_cfg.get("enabled", True):
        return []

    area_vector = metrics.get("area_vector")
    if area_vector is not None and (not isinstance(area_vector, (list, tuple)) or len(area_vector) != 12):
        raise ValueError("area_vector must be length 12 when provided")

    entropy = float(metrics.get("entropy", 0.0))
    coverage = float(metrics.get("coverage", 0.0))
    stability_index = float(metrics.get("stability_index", 0.0))
    dominant_share = compute_dominant_area_share(area_vector) if area_vector else 0.0

    # Unique areas visited (from trajectory or area_vector non-zero count)
    unique_areas = 0
    if area_vector and isinstance(area_vector, (list, tuple)):
        unique_areas = sum(1 for x in area_vector if (x if isinstance(x, (int, float)) else 0) > 0)
    trajectory = metrics.get("trajectory") or {}
    compressed = trajectory.get("compressed") if isinstance(trajectory, dict) else []
    if compressed and isinstance(compressed, (list, tuple)):
        unique_areas = max(unique_areas, len(compressed))

    diagnostics: list[dict[str, Any]] = []
    ent_thresh = float(mono_cfg.get("entropy_threshold", 0.35))
    cov_thresh = float(mono_cfg.get("coverage_threshold", 0.20))
    share_thresh = float(mono_cfg.get("dominant_area_share_threshold", 0.65))
    stability_high = float(mono_cfg.get("stability_high_threshold", 0.70))
    unique_max = int(mono_cfg.get("unique_areas_max", 2))

    # Base trigger: entropy < threshold; strengthened when coverage also low
    if entropy < ent_thresh:
        evidence = {"entropy": entropy, "coverage": coverage, "dominant_area_share": dominant_share}
        msg = "Low entropy and low coverage indicate structurally narrow concentration." if coverage < cov_thresh else "Low entropy indicates structurally narrow concentration."
        diagnostics.append({
            "diagnostic_code": "STRUCTURAL_MONOTONY",
            "severity": "medium",
            "message": msg,
            "evidence": evidence,
            "source_detector": "monotony_detector",
        })

    # Optional: excessive dominant share
    if dominant_share > share_thresh:
        diagnostics.append({
            "diagnostic_code": "STRUCTURAL_MONOTONY_DOMINANT_SHARE",
            "severity": "medium",
            "message": "Excessive dominance of one area.",
            "evidence": {"dominant_area_share": dominant_share},
            "source_detector": "monotony_detector",
        })

    # Optional: high stability and very few areas
    if stability_index > stability_high and unique_areas <= unique_max:
        diagnostics.append({
            "diagnostic_code": "STRUCTURAL_MONOTONY_LOW_DIVERSITY",
            "severity": "medium",
            "message": "High stability and few areas indicate structurally narrow concentration.",
            "evidence": {"stability_index": stability_index, "unique_areas_visited": unique_areas},
            "source_detector": "monotony_detector",
        })

    return diagnostics
