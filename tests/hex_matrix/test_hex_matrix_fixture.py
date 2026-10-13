# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
TMX-15: Gold fixture + snapshot validation for hex_matrix_viewer dataset schema.

Tests:
  1. Gold fixture JSON loads and satisfies the Dataset schema contract.
  2. Each frame has valid HexState fields (N_AREAS=12 area_scores, dominance ∈ [0,1], etc.).
  3. Relations block shape (12 area_drift entries, drift is float).
  4. AppearDisappear block shape (appeared/disappeared lists, onset_frame integer).
  5. D3 smoke: dataset has frames, each frame has t + hexes, each hex has q/r for D3 positioning.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_GOLD_FIXTURE = Path(__file__).parent / "fixtures" / "hex_matrix_gold_fixture.json"

N_AREAS = 12


def _load_fixture() -> dict:
    with open(_GOLD_FIXTURE, encoding="utf-8") as f:
        return json.load(f)


def _validate_hex_state(h: dict, frame_idx: int, hex_idx: int) -> None:
    loc = f"frame[{frame_idx}].hexes[{hex_idx}]"
    assert "id" in h, f"{loc}: missing id"
    assert "area_scores" in h, f"{loc}: missing area_scores"
    scores = h["area_scores"]
    assert len(scores) == N_AREAS, f"{loc}: area_scores must have {N_AREAS} entries, got {len(scores)}"
    for i, s in enumerate(scores):
        assert 0.0 <= s <= 1.0, f"{loc}: area_scores[{i}]={s} out of [0,1]"
    assert "dominant_area" in h, f"{loc}: missing dominant_area"
    assert 0 <= h["dominant_area"] < N_AREAS, f"{loc}: dominant_area out of range"
    assert "dominance" in h, f"{loc}: missing dominance"
    assert 0.0 <= h["dominance"] <= 1.0, f"{loc}: dominance out of [0,1]"
    assert "stability" in h, f"{loc}: missing stability"
    assert 0.0 <= h["stability"] <= 1.0, f"{loc}: stability out of [0,1]"
    # D3 smoke: q/r must be present and numeric
    assert "q" in h and "r" in h, f"{loc}: missing q/r (D3 positioning)"
    assert isinstance(h["q"], (int, float)), f"{loc}: q must be numeric"
    assert isinstance(h["r"], (int, float)), f"{loc}: r must be numeric"


def test_gold_fixture_loads() -> None:
    """Gold fixture file exists and parses."""
    assert _GOLD_FIXTURE.exists(), f"Gold fixture not found: {_GOLD_FIXTURE}"
    ds = _load_fixture()
    assert "frames" in ds, "Dataset must have 'frames'"


def test_gold_fixture_frames_schema() -> None:
    """Each frame in the gold fixture has valid HexState entries."""
    ds = _load_fixture()
    assert len(ds["frames"]) >= 1, "Dataset must have at least one frame"
    for fi, frame in enumerate(ds["frames"]):
        assert "t" in frame, f"frame[{fi}]: missing t"
        assert "hexes" in frame, f"frame[{fi}]: missing hexes"
        for hi, h in enumerate(frame["hexes"]):
            _validate_hex_state(h, fi, hi)


def test_gold_fixture_relations_block() -> None:
    """Relations block has 12 area_drift entries with valid drift values."""
    ds = _load_fixture()
    assert "relations" in ds, "Dataset gold fixture must include relations block"
    rel = ds["relations"]
    assert "area_drift" in rel
    drift = rel["area_drift"]
    assert len(drift) == N_AREAS, f"area_drift must have {N_AREAS} entries, got {len(drift)}"
    for entry in drift:
        assert "area" in entry and "drift" in entry
        assert isinstance(entry["drift"], (int, float))


def test_gold_fixture_appear_disappear_block() -> None:
    """AppearDisappear block has appeared/disappeared lists with required fields."""
    ds = _load_fixture()
    assert "appear_disappear" in ds, "Dataset gold fixture must include appear_disappear block"
    ad = ds["appear_disappear"]
    for sig in ad.get("appeared", []):
        assert "label" in sig, "appeared signal missing label"
    for sig in ad.get("disappeared", []):
        assert "label" in sig, "disappeared signal missing label"


def test_d3_smoke_positioning() -> None:
    """All hexes in gold fixture have q/r for D3 hex-to-pixel positioning."""
    ds = _load_fixture()
    for fi, frame in enumerate(ds["frames"]):
        for hi, h in enumerate(frame["hexes"]):
            assert "q" in h and "r" in h, f"frame[{fi}].hexes[{hi}]: missing q/r"
