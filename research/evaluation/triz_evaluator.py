# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Qualitative profile fit scoring for benchmark stability (demo-readiness, not scientific truth)."""

from __future__ import annotations

from typing import Any, Literal

ProfileLevel = Literal["low", "medium", "high", "stable", "fragmented"]

_LEVEL_TO_TARGET: dict[str, float] = {
    "low": 0.15,
    "medium": 0.45,
    "high": 0.75,
    "stable": 0.7,
    "fragmented": 0.25,
}


def _target(profile_key: str, expected: dict[str, str]) -> float:
    v = (expected.get(profile_key) or "medium").lower()
    return _LEVEL_TO_TARGET.get(v, 0.45)


def _actual_policy(report: dict[str, Any]) -> float:
    return float(report.get("global_tension_index", report.get("global_tension_score", 0)))


def _actual_innovation(report: dict[str, Any]) -> float:
    return float(report.get("innovation_pressure_index", report.get("innovation_pressure_score", 0)))


def _actual_narrative_stability(report: dict[str, Any]) -> float:
    n = report.get("narratives") or [{}]
    return float(n[0].get("stability", 0)) if n else 0.0


def _actual_narrative_penetration(report: dict[str, Any]) -> float:
    n = report.get("narratives") or [{}]
    return float(n[0].get("penetration", 0)) if n else 0.0


def profile_fit_score(actual: float, target: float) -> float:
    """1 - normalized MAE in [0,1]."""
    err = abs(actual - target)
    return max(0.0, min(1.0, 1.0 - err))


def evaluate_policy_detector(report: dict[str, Any], expected_profile: dict[str, str]) -> dict[str, Any]:
    t = _target("contradiction", expected_profile)
    a = _actual_policy(report)
    return {
        "actual_tension": round(a, 6),
        "expected_target": t,
        "profile_fit_score": round(profile_fit_score(a, t), 6),
    }


def evaluate_innovation_radar(report: dict[str, Any], expected_profile: dict[str, str]) -> dict[str, Any]:
    t = _target("innovation", expected_profile)
    a = _actual_innovation(report)
    return {
        "actual_innovation": round(a, 6),
        "expected_target": t,
        "profile_fit_score": round(profile_fit_score(a, t), 6),
    }


def evaluate_narrative_monitor(full_triz: dict[str, Any], expected_profile: dict[str, str]) -> dict[str, Any]:
    prop = (expected_profile.get("propagation") or "medium").lower()
    if prop == "stable":
        target = 0.65
        a = _actual_narrative_stability(full_triz)
    elif prop == "fragmented":
        target = 0.35
        a = _actual_narrative_penetration(full_triz)
    else:
        target = 0.5
        a = (_actual_narrative_stability(full_triz) + _actual_narrative_penetration(full_triz)) / 2.0
    return {
        "actual": round(a, 6),
        "expected_target": target,
        "profile_fit_score": round(profile_fit_score(a, target), 6),
    }
