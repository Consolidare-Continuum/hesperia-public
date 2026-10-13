# HESPERIA — Session topology compatibility surface (NLP package).
# Re-exports research implementation + sentence-level ``segment_session_text`` and dynamics helper.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import re
from typing import Any

import research.clinical_tfp.session_topology as _clinical_topology

AREA_CURVE_MAP = _clinical_topology.AREA_CURVE_MAP
CURVE_CALIBRATION_REFERENCE = _clinical_topology.CURVE_CALIBRATION_REFERENCE
DEFAULT_SESSION_TOPOLOGY_RUN_PARAMS = _clinical_topology.DEFAULT_SESSION_TOPOLOGY_RUN_PARAMS
build_area_curves = _clinical_topology.build_area_curves
build_session_state_sequence = _clinical_topology.build_session_state_sequence
detect_aggression_escalation = _clinical_topology.detect_aggression_escalation
detect_defense_shifts = _clinical_topology.detect_defense_shifts
detect_state_transitions = _clinical_topology.detect_state_transitions
extract_area_curve = _clinical_topology.extract_area_curve
postprocess_area_curves = _clinical_topology.postprocess_area_curves
segment_session = _clinical_topology.segment_session

__all__ = [
    "AREA_CURVE_MAP",
    "CURVE_CALIBRATION_REFERENCE",
    "DEFAULT_SESSION_TOPOLOGY_RUN_PARAMS",
    "analyze_session_segments",
    "build_area_curves",
    "build_session_state_sequence",
    "compute_topology_dynamics",
    "detect_aggression_escalation",
    "detect_defense_shifts",
    "detect_state_transitions",
    "extract_area_curve",
    "postprocess_area_curves",
    "run_session_topology",
    "segment_session",
    "segment_session_text",
]


def segment_session_text(text: str) -> list[str]:
    """Coarse sentence-like segments for NLP/tests (distinct from token-window ``segment_session``)."""
    if not text or not isinstance(text, str) or not text.strip():
        return []
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    out: list[str] = []
    for p in parts:
        s = p.strip()
        if not s:
            continue
        if len(s) > 1:
            s = s.rstrip(".!?")
        out.append(s)
    return out


def analyze_session_segments(text: str, window_size: int = 80, **kwargs: Any) -> list[dict[str, Any]]:
    """Token-window segments + ``segment_id`` / ``text`` fields expected by NLP tests."""
    segs = _clinical_topology.segment_session(text, window_size=window_size)
    rows = _clinical_topology.analyze_session_segments(text, window_size=window_size, **kwargs)
    merged: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        r = dict(row)
        r["segment_id"] = i
        if i <= len(segs):
            r["text"] = segs[i - 1]
        merged.append(r)
    return merged


def _dominant_area(areas: dict[str, Any]) -> str:
    if not areas:
        return ""
    return max(areas.items(), key=lambda x: float(x[1] or 0))[0]


def compute_topology_dynamics(segment_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Dominant-area trace + 1-based shift indices + A4 peak segment (tests + NLP helpers)."""
    if not segment_results:
        return {
            "dominant_area_sequence": [],
            "defense_shift_points": [],
            "affect_peaks": [],
            "max_aggression_peak": None,
        }
    seq = [_dominant_area(r.get("areas") or {}) for r in segment_results]
    defense_shift_points: list[int] = []
    for i in range(1, len(seq)):
        if seq[i] != seq[i - 1]:
            defense_shift_points.append(i + 1)
    peak_idx: int | None = None
    best_a4 = -1.0
    for i, r in enumerate(segment_results):
        a4 = float((r.get("areas") or {}).get("A4", 0) or 0)
        if a4 > best_a4:
            best_a4 = a4
            peak_idx = i + 1
    if best_a4 <= 0:
        peak_idx = None
    return {
        "dominant_area_sequence": seq,
        "defense_shift_points": defense_shift_points,
        "affect_peaks": [],
        "max_aggression_peak": peak_idx,
    }


def run_session_topology(text: str, **kwargs: Any) -> dict[str, Any]:
    """Same as research implementation plus ``dynamics`` block for NLP/tests."""
    out = dict(_clinical_topology.run_session_topology(text, **kwargs))
    segs = out.get("segments_stable") or out.get("segments") or []
    out["dynamics"] = compute_topology_dynamics(segs)
    return out
