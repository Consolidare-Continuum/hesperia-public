"""Trajectory features over ordered segment outputs (e.g. dominant microcell per segment)."""

from __future__ import annotations

from typing import Any


def trajectory_over_segments(segment_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    """
    ``segment_summaries``: one dict per segment with optional ``dominant_slot`` (int) and ``mass`` (float).
    Returns JSON-serializable trajectory stats.
    """
    slots: list[int | None] = []
    masses: list[float] = []
    for s in segment_summaries:
        ds = s.get("dominant_slot")
        slots.append(int(ds) if ds is not None else None)
        try:
            masses.append(float(s.get("mass") or 0.0))
        except (TypeError, ValueError):
            masses.append(0.0)
    moves = 0
    jump_distance = 0.0
    curvature = 0.0
    prev = None
    prev_delta = None
    for s in slots:
        if s is None:
            continue
        if prev is not None and s != prev:
            moves += 1
            delta = float(abs(s - prev))
            jump_distance += delta
            if prev_delta is not None:
                curvature += abs(delta - prev_delta)
            prev_delta = delta
        prev = s
    stability_window = 0.0
    if len(slots) > 1:
        stability_window = 1.0 - (moves / max(1, len(slots) - 1))
    total_mass = sum(masses)
    retention_ratio = 0.0
    if masses:
        retention_ratio = float(masses[-1]) / max(float(masses[0]), 1e-12)
    return {
        "segment_count": len(segment_summaries),
        "dominant_slots": slots,
        "transition_count": moves,
        "jump_distance": round(jump_distance, 6),
        "curvature": round(curvature, 6),
        "stability_window": round(max(0.0, min(1.0, stability_window)), 6),
        "retention_ratio": round(max(0.0, retention_ratio), 6),
        "total_mass": round(total_mass, 6),
    }
