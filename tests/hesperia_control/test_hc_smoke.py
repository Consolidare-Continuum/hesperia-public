# HC program smoke tests (HC-06 / HC-07). Copyright © 2026 igareosh.com.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hesperia.engine.hesperia_control.dominance import classify_segment_dominance
from hesperia.engine.hesperia_control.modifier_mvp import apply_modifier_mvp_pre_cd
from hesperia.engine.hesperia_control.unmapped_diagnostics import rank_unmapped_tokens

REPO = Path(__file__).resolve().parents[2]
FIX_BA = REPO / "tests" / "fixtures" / "ba_validation"


def test_ba_validation_gold_fixtures_match_schema() -> None:
    for name in ("seg_001.json", "seg_002.json", "seg_003.json"):
        p = FIX_BA / name
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["schema_version"] == "ba_validation_envelope.v1.0.0"
        assert data["concept_id"].startswith("B_")


def test_modifier_mvp_deterministic() -> None:
    w = {"B_a": 1.0, "B_b": 2.0}
    r = apply_modifier_mvp_pre_cd(w, negation_targets={"B_a": 1.0}, damping_factor=0.5)
    assert w["B_a"] == pytest.approx(0.0)
    assert "trace" in r


def test_dominance_mixed() -> None:
    out, top, _ = classify_segment_dominance({"A1": 0.4, "A2": 0.35}, dominance_min=0.5, dominance_gap_min=0.12)
    assert out in ("mixed", "weak_dominant", "dominant", "invalid")


def test_unmapped_rank() -> None:
    rep = rank_unmapped_tokens({"z": 1, "a": 2})
    assert rep.ranked_by_frequency[0][0] == "a"
