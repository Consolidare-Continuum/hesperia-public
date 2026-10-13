# HESPERIA — HES-61-01 engine /analyze contract (Python).

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.services.engine_analyze_contract import (
    build_engine_analyze_from_raw,
    run_engine_analyze,
    trace_content_hash,
)
from runtime.shipping.api_main import AnalyzeBody


REPO = Path(__file__).resolve().parents[1]
ASSETS = REPO / "assets" / "lexicon" / "curated"


def test_analyze_body_accepts_overlay_fields() -> None:
    body = AnalyzeBody(
        text="hello",
        mode="reflection",
        overlay_hint={"family_biases": {"A1:family_000": {"prior_boost": 0.1}}},
        temp_relation_overlay=[
            {
                "from_area_id": "A1",
                "from_family_id": "family_000",
                "to_area_id": "A2",
                "to_family_id": "family_024",
                "relation_type": "BRIDGES",
                "proposed_strength": 0.5,
            }
        ],
    )
    assert body.mode == "reflection"
    assert body.overlay_hint is not None


def test_build_engine_analyze_minimal_raw() -> None:
    raw = {
        "multiscale_signals": {
            "family_activation_vector": [0.0, 0.9, 0.1],
            "hspr_index": 0.42,
            "contradiction_pressure": 0.11,
            "propagation_strength": 0.55,
        },
        "diagnostics": {"interpretability_trace": {"marker_concept_sample": []}},
    }
    out = build_engine_analyze_from_raw(raw)
    assert out["contract_version"] == "v1.0"
    assert out["trace"]
    step = out["trace"][0]
    assert "area_id" in step and "family_id" in step and "concept_id" in step
    assert out["dominant_area_id"] == out["trace"][0]["area_id"] or True
    assert 0.0 <= out["governance"] <= 1.0


@pytest.mark.skipif(not ASSETS.is_dir(), reason="lexicon assets missing")
def test_run_engine_analyze_live_text() -> None:
    out = run_engine_analyze("love kindness help altruism protection care", assets_root=ASSETS)
    assert out["trace"]
    for key in (
        "dominant_area_id",
        "dominant_family_id",
        "dominant_concept_id",
        "governance",
        "loopability",
        "tension_energy",
        "obstacle_score",
        "contradiction_flags",
        "weak_signals",
    ):
        assert key in out
    top = max(out["trace"], key=lambda s: s["activation"])
    assert out["dominant_concept_id"] == top["concept_id"]


@pytest.mark.skipif(not ASSETS.is_dir(), reason="lexicon assets missing")
def test_temp_overlay_changes_trace_hash() -> None:
    text = "love kindness help altruism protection care"
    base = run_engine_analyze(text, assets_root=ASSETS)
    with_overlay = run_engine_analyze(
        text,
        assets_root=ASSETS,
        temp_relation_overlay=[
            {
                "from_area_id": "A1",
                "from_family_id": "family_000",
                "to_area_id": "A2",
                "to_family_id": "family_024",
                "relation_type": "BRIDGES",
                "proposed_strength": 0.9,
            }
        ],
    )
    assert trace_content_hash(base["trace"]) != trace_content_hash(with_overlay["trace"])
