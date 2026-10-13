"""Failure mode registry for engine runs."""

from __future__ import annotations

from typing import Any

from core.dynamics.numeric import EPS

FAILURE_CATEGORIES = (
    "saturation_collapse",
    "oscillation",
    "dominance_lock",
    "fragmentation",
    "drift",
)


def classify_failures(run_output: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    traj = run_output.get("segment_trajectory") or {}
    dominance = run_output.get("hex_concentration", 0.0)
    dispersion = run_output.get("hex_dispersion", 0.0)
    jump_distance = float(traj.get("jump_distance", 0.0))
    curvature = float(traj.get("curvature", 0.0))
    retention_ratio = float(traj.get("retention_ratio", 0.0))

    if retention_ratio <= EPS:
        flags.append("saturation_collapse")
    if curvature > 10.0 and jump_distance > 10.0:
        flags.append("oscillation")
    if dominance >= 0.95:
        flags.append("dominance_lock")
    if dispersion >= 0.9 and dominance <= 0.2:
        flags.append("fragmentation")
    if jump_distance > 20.0:
        flags.append("drift")
    return sorted(set(flags))

