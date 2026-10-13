# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
CHI-003-02 calibration gate: ``compute_areas_working`` (session working-theme dual signal,
per the CHI-003-01 Colombo verdict) against the 14 real TFP sessions on disk in
outputs/tfp/runs/tfp_gena_*_corpuscalib. Fixture extracted from those real runs' real
09_session_topology.json segments / 02_session_tfp_stages.json areas_final — numeric area
vectors only, no session text.
"""

from __future__ import annotations

import json
from pathlib import Path

from research.clinical_tfp.interpretation import get_dominant_area
from research.clinical_tfp.session_topology import (
    TFP_WORKING_THEME_WARMUP_SEGMENTS,
    TFP_WORKING_THEME_WARMUP_WEIGHT,
    compute_areas_working,
)

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "chi003_areas_working_calibration.json"


def _load_sessions() -> list[dict]:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))["sessions"]


def test_fixture_has_all_14_real_sessions() -> None:
    sessions = _load_sessions()
    assert len(sessions) == 14
    # areas_final dominant is A10 in all 14 (CHI-003 finding) -- fixture sanity, not the point under test.
    assert all(get_dominant_area(s["areas_final"]) == "A10" for s in sessions)


def test_areas_working_is_a_valid_distribution() -> None:
    for s in _load_sessions():
        aw = compute_areas_working(s["segments"])
        assert aw, s["session_label"]
        assert abs(sum(aw.values()) - 1.0) < 1e-6, s["session_label"]
        assert all(v >= 0.0 for v in aw.values()), s["session_label"]


def test_areas_working_calibration_matches_pinned_constants() -> None:
    """
    Pins the calibrated constants against the real 14-session corpus. A change to
    TFP_WORKING_THEME_WARMUP_SEGMENTS/WEIGHT (or to compute_areas_working's math) that
    moves this must be a conscious recalibration, not a silent drift.
    """
    assert TFP_WORKING_THEME_WARMUP_SEGMENTS == 2
    assert TFP_WORKING_THEME_WARMUP_WEIGHT == 0.25

    sessions = _load_sessions()
    flips = 0
    flip_targets: set[str] = set()
    for s in sessions:
        dom_final = get_dominant_area(s["areas_final"])
        dom_working = get_dominant_area(compute_areas_working(s["segments"]))
        if dom_working != dom_final:
            flips += 1
            flip_targets.add(dom_working)

    # Meaningfully different from areas_final (not a no-op pass-through) but not a
    # near-universal flip either (would suggest an over-aggressive down-weight, the same
    # failure mode CHI-003-01 rejected in untuned Phase1Theta). 7/14 pinned exactly.
    assert flips == 7
    # Flips land on more than one area -- not just replicating Phase1Theta's near-universal
    # "replace with A1" pattern (CHI-003 spec §3: decay disagreements were almost always A1).
    assert flip_targets == {"A1", "A6"}


def test_areas_working_ignores_segments_beyond_warmup_uniformly() -> None:
    """Two sessions with identical post-warmup segments but different warmup segments
    should differ only by the warmup contribution, not diverge arbitrarily."""
    sessions = _load_sessions()
    base = next(s for s in sessions if len(s["segments"]) >= 4)
    segs = base["segments"]
    warmup, rest = segs[:2], segs[2:]

    aw_real = compute_areas_working(segs)
    aw_flat = compute_areas_working(rest)  # no warmup segments at all -> pure rest average
    aw_double_warmup = compute_areas_working(warmup + warmup + rest)

    assert aw_real != aw_flat
    # Doubling the (down-weighted) warmup segments should nudge, not flip wildly.
    assert get_dominant_area(aw_double_warmup) in (
        get_dominant_area(aw_real),
        get_dominant_area(aw_flat),
    )


def test_areas_working_has_no_field_dynamics_dependency() -> None:
    """CHI-003-01 verdict: no Phase1Theta / Field Dynamics defaults in this wave."""
    import ast

    import research.clinical_tfp.session_topology as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any("dynamics" in m or "phase1" in m for m in imported_modules)
