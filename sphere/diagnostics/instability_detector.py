# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Rhetorical instability detector.
Detects unstable structural movement across discourse flow. Machine-clean diagnostics only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SPEC = _REPO_ROOT / "spec" / "diagnostic_rules.yaml"


def _load_config(config: dict[str, Any]) -> dict[str, Any]:
    out = dict(config)
    path = config.get("diagnostic_rules_path") or _DEFAULT_SPEC
    if path and Path(path).exists():
        with open(path, encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        if spec and "instability" in spec:
            out.setdefault("instability", spec["instability"])
    if "instability" not in out:
        out["instability"] = {
            "enabled": True,
            "curvature_threshold": 1.20,
            "severe_curvature_threshold": 1.50,
            "jump_rate_threshold": 0.30,
            "severe_jump_rate_threshold": 0.50,
            "low_stability_threshold": 0.15,
        }
    return out


def _jump_rate_value(metrics: dict[str, Any]) -> float:
    v = metrics.get("jump_rate")
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict) and "jump_rate" in v:
        return float(v["jump_rate"])
    return 0.0


def detect_rhetorical_instability(metrics: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Detect rhetorical instability from metrics. Returns list of canonical diagnostic objects.
    v1: curvature > 1.20; stronger with jump_rate > 0.30; severe if curvature > 1.50 or jump_rate > 0.50 or stability < 0.15.
    """
    cfg = _load_config(config)
    inst_cfg = cfg.get("instability", {})
    if not inst_cfg.get("enabled", True):
        return []

    curvature = float(metrics.get("curvature", 0.0))
    jump_rate = _jump_rate_value(metrics)
    stability_index = float(metrics.get("stability_index", 0.0))

    diagnostics: list[dict[str, Any]] = []
    curv_thresh = float(inst_cfg.get("curvature_threshold", 1.20))
    severe_curv = float(inst_cfg.get("severe_curvature_threshold", 1.50))
    jump_thresh = float(inst_cfg.get("jump_rate_threshold", 0.30))
    severe_jump = float(inst_cfg.get("severe_jump_rate_threshold", 0.50))
    low_stab = float(inst_cfg.get("low_stability_threshold", 0.15))

    # Severe: curvature > 1.50 or jump_rate > 0.50 or stability_index < 0.15
    if curvature > severe_curv or jump_rate > severe_jump or stability_index < low_stab:
        diagnostics.append({
            "diagnostic_code": "RHETORICAL_INSTABILITY",
            "severity": "high",
            "message": "Curvature, jump rate, or stability indicates severe unstable structural movement.",
            "evidence": {"curvature": curvature, "jump_rate": jump_rate, "stability_index": stability_index},
            "source_detector": "instability_detector",
        })
        return diagnostics

    # Base: curvature > 1.20
    if curvature > curv_thresh:
        msg = "Curvature above threshold indicates unstable structural movement."
        if jump_rate > jump_thresh:
            msg = "Curvature and jump rate above threshold indicate unstable structural movement."
        diagnostics.append({
            "diagnostic_code": "RHETORICAL_INSTABILITY",
            "severity": "high",
            "message": msg,
            "evidence": {"curvature": curvature, "jump_rate": jump_rate, "stability_index": stability_index},
            "source_detector": "instability_detector",
        })

    return diagnostics
