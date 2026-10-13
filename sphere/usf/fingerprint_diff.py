# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
USF fingerprint comparison toolkit: deterministic comparison between two USFs.
Works with sphere.usf.usf_compare.compare_usf().
"""

from __future__ import annotations

from typing import Any

from sphere.usf.drift import (
    compute_drift_score,
    MINOR_CHANGE_THRESHOLD,
    MAJOR_CHANGE_THRESHOLD,
)
from sphere.usf.usf_compare import compare_usf


def _fingerprint_from_usf(usf: dict[str, Any]) -> dict[str, Any]:
    """Build fingerprint dict for distance (state keys + active_events)."""
    fp = dict(usf.get("fingerprint") or {})
    for k in ("entropy_state", "tension_state", "propagation_state"):
        if k in usf and k not in fp:
            fp[k] = usf[k]
    return fp


def compare_structural_fingerprint(
    usf_a: dict[str, Any],
    usf_b: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare two USF structural fingerprints.
    Returns dict with distance, drift_class, changed_fields, dominant_area_change, entropy_delta.
    """
    fp_a = _fingerprint_from_usf(usf_a)
    fp_b = _fingerprint_from_usf(usf_b)
    distance = compute_drift_score(fp_a, fp_b)
    drift_class = classify_drift(distance)

    # Changed state keys
    changed_fields = [
        k for k in ("structural_state", "dominant_area_id", "entropy_state", "tension_state", "propagation_state")
        if fp_a.get(k) != fp_b.get(k)
    ]
    events_a = set(fp_a.get("active_events") or [])
    events_b = set(fp_b.get("active_events") or [])
    if events_a != events_b:
        changed_fields.append("active_events")

    # Dominant area change
    dominant_area_change = (fp_a.get("dominant_area_id") != fp_b.get("dominant_area_id"))

    # Entropy delta from raw_metrics
    raw_a = usf_a.get("raw_metrics") or {}
    raw_b = usf_b.get("raw_metrics") or {}
    ea = raw_a.get("entropy")
    eb = raw_b.get("entropy")
    if ea is not None and eb is not None:
        try:
            entropy_delta = float(eb) - float(ea)
        except (TypeError, ValueError):
            entropy_delta = None
    else:
        entropy_delta = None

    return {
        "distance": distance,
        "drift_class": drift_class,
        "changed_fields": changed_fields,
        "dominant_area_change": dominant_area_change,
        "entropy_delta": entropy_delta,
    }


def fingerprint_distance(usf_a: dict[str, Any], usf_b: dict[str, Any]) -> float:
    """Scalar fingerprint distance (drift score) between two USFs."""
    fp_a = _fingerprint_from_usf(usf_a)
    fp_b = _fingerprint_from_usf(usf_b)
    return compute_drift_score(fp_a, fp_b)


def classify_drift(distance: float) -> str:
    """Classify drift by distance: stable, minor, major, semantic_shift."""
    if distance <= 0.0:
        return "stable"
    if distance < MINOR_CHANGE_THRESHOLD:
        return "minor"
    if distance < MAJOR_CHANGE_THRESHOLD:
        return "major"
    return "semantic_shift"


__all__ = [
    "compare_structural_fingerprint",
    "fingerprint_distance",
    "classify_drift",
]
