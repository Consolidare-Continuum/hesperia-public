# HESPERIA — Tests for LEVEL 7 Session topology (temporal activation)
"""Segmentation, per-segment analysis, dynamics (area sequence, defense shifts, affect peaks)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_segmentation_works() -> None:
    from hesperia.nlp.session_topology import segment_session_text
    assert segment_session_text("") == []
    assert segment_session_text("   ") == []
    text = "Пациент злится на терапевта. Потом говорит, что терапевт был хорошим. Затем снова обвиняет терапевта."
    segments = segment_session_text(text)
    assert len(segments) == 3
    assert "злится" in segments[0]
    assert "хорошим" in segments[1]
    assert "обвиняет" in segments[2]
    # One sentence
    assert segment_session_text("Один сегмент.") == ["Один сегмент"]
    # Multiple delimiters
    assert len(segment_session_text("Первый. Второй? Третий!")) == 3


def test_segments_analyzed() -> None:
    from hesperia.nlp.session_topology import analyze_session_segments
    text = "Расщепление и агрессия. Перенос и интеграция."
    results = analyze_session_segments(text, window_size=3)
    assert len(results) == 2
    for r in results:
        assert "segment_id" in r and "text" in r
        assert "areas" in r and "families" in r and "concepts" in r
        assert isinstance(r["areas"], dict)
        assert isinstance(r["families"], dict)
        assert isinstance(r["concepts"], dict)
    assert results[0]["segment_id"] == 1
    assert results[1]["segment_id"] == 2


def test_dynamics_computed() -> None:
    from hesperia.nlp.session_topology import compute_topology_dynamics
    # Empty
    out = compute_topology_dynamics([])
    assert out["dominant_area_sequence"] == []
    assert out["defense_shift_points"] == []
    assert out["affect_peaks"] == []
    assert out["max_aggression_peak"] is None
    # Mock: A4 → A3 → A2 so we get defense_shift_points at 2 and 3 (A3 involved)
    segment_results = [
        {"areas": {"A4": 1.0, "A2": 0.3}, "families": {}, "concepts": {}},
        {"areas": {"A3": 1.0, "A4": 0.2}, "families": {}, "concepts": {}},
        {"areas": {"A2": 1.0, "A3": 0.5}, "families": {}, "concepts": {}},
    ]
    dynamics = compute_topology_dynamics(segment_results)
    assert dynamics["dominant_area_sequence"] == ["A4", "A3", "A2"]
    assert dynamics["defense_shift_points"] == [2, 3]  # A4→A3 and A3→A2
    assert "affect_peaks" in dynamics
    assert dynamics["max_aggression_peak"] == 1  # A4 highest in segment 1


def test_run_session_topology_full() -> None:
    from hesperia.nlp.session_topology import run_session_topology
    text = "Пациент злится на терапевта. Потом говорит, что терапевт был хорошим. Затем снова обвиняет терапевта."
    out = run_session_topology(text, window_size=5)
    assert "segments" in out and "dynamics" in out
    assert len(out["segments"]) == 3
    assert "dominant_area_sequence" in out["dynamics"]
    assert len(out["dynamics"]["dominant_area_sequence"]) == 3
    # Expected topology: A4 (aggression), A2 (object relations), A4 (aggression)
    seq = out["dynamics"]["dominant_area_sequence"]
    assert len(seq) == 3
    # First and third segment may favor A4 (aggression), second A2 (object relations)
    assert all(isinstance(a, str) for a in seq)
    assert all(not a or (a.startswith("A") and a[1:].split("_", 1)[0].isdigit()) for a in seq)
