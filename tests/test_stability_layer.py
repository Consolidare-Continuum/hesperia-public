# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Δ (Delta) stability layer tests.
Deterministic structural correction: clean pipeline → low anomaly_score;
forced topology collision → high anomaly_score; stability output passed to L7.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.stability.stability_delta import (
    ANOMALY_SCORE_THRESHOLD_LOW_CONFIDENCE,
    run_stability,
)


def _make_clean_layers() -> dict:
    """Minimal L1/L2/L6 state that should yield low anomaly (contained, no drift, no loops)."""
    return {
        1: {
            "DOMINANT_AREA_ID": 0,
            "DOMINANT_FAMILY_ID": 15,
            "AREA_SPREAD": 0.08,
            "COVERAGE_RATIO": 0.5,
        },
        2: {
            "CROSS_AREA_RATIO": 0.0,
            "LOOP_DENSITY": 0.0,
            "LOOP_COUNT": 0,
            "VISITED_IDS": [14, 15, 16],
        },
        6: {
            "CONDITION_NUMBER": 1.0,
            "DOMINANCE_CURVATURE": 0.0,
            "ENTROPY_CURVATURE": 0.0,
            "GLOBAL_STABILITY_SCORE": 1.0,
        },
    }


def _make_collision_layers() -> dict:
    """State that triggers AREA_COLLISION + FAMILY_DRIFT (dominant family not in visited)."""
    return {
        1: {
            "DOMINANT_AREA_ID": 0,
            "DOMINANT_FAMILY_ID": 99,
            "AREA_SPREAD": 0.6,
        },
        2: {
            "CROSS_AREA_RATIO": 0.55,
            "LOOP_DENSITY": 0.0,
            "LOOP_COUNT": 0,
            "VISITED_IDS": [0, 1, 2, 3],
        },
        6: {
            "CONDITION_NUMBER": 1.0,
            "DOMINANCE_CURVATURE": 0.0,
            "ENTROPY_CURVATURE": 0.0,
            "GLOBAL_STABILITY_SCORE": 1.0,
        },
    }


def test_stability_clean_pipeline_low_anomaly() -> None:
    """Clean pipeline state → anomaly_score low (< threshold)."""
    layers = _make_clean_layers()
    out = run_stability(layers)
    assert "anomaly_score" in out
    assert "instability_flags" in out
    assert "corrective_bias" in out
    assert "confidence_adjustment" in out
    assert out["anomaly_score"] < ANOMALY_SCORE_THRESHOLD_LOW_CONFIDENCE
    assert len(out["instability_flags"]) == 0


def test_stability_forced_collision_high_anomaly() -> None:
    """Forced topology collision (high cross-area, family drift) → anomaly_score high."""
    layers = _make_collision_layers()
    out = run_stability(layers)
    assert out["anomaly_score"] >= ANOMALY_SCORE_THRESHOLD_LOW_CONFIDENCE
    assert len(out["instability_flags"]) >= 1
    assert "corrective_bias" in out
    assert out.get("corrective_bias", {}).get("trust_demotion") is True


def test_stability_output_structure() -> None:
    """Stability output has required keys."""
    out = run_stability(_make_clean_layers())
    assert isinstance(out["anomaly_score"], (int, float))
    assert isinstance(out["instability_flags"], list)
    assert isinstance(out["corrective_bias"], dict)
    assert isinstance(out["confidence_adjustment"], (int, float))


def test_stability_passed_to_l7() -> None:
    """Full pipeline run: Δ stability runs after L6, stored in diagnostics and L7 can demote tag."""
    from core.attribution.structural import (
        attribute,
        load_dict_a,
        load_dict_b,
        normalize,
        tokenize,
    )
    from core.contracts.layer_contract import LayerInput
    from core.layers import build_canonical_stub_adjacency, load_defaults
    from core.stability import run_stability
    from sphere.pipeline.layer_registry import LAYERS
    from sphere.pipeline.pipeline_state import PipelineState

    text = "justice fairness order"
    assets = _REPO / "assets" / "lexicon" / "curated"
    dict_a = load_dict_a(assets_root=assets) or {}
    dict_b = load_dict_b()
    defaults = load_defaults()
    F = int(defaults.get("F", 288))
    A = int(defaults.get("A", 12))
    D = int(defaults.get("MAX_ALLOWED_DEPTH", 8))
    tokens = tokenize(normalize(text))
    matched, _ = attribute(tokens, dict_a, dict_b)
    hits = [0] * F
    for fg, _ in matched:
        if 0 <= fg < F:
            hits[fg] += 1
    adjacency = build_canonical_stub_adjacency(F, A)
    state = PipelineState()
    metadata = {
        "F": F,
        "A": A,
        "eps": float(defaults.get("eps", 1e-9)),
        "defaults": defaults,
        "matched": matched,
        "hits": hits,
        "adjacency": adjacency,
        "profile_id": None,
        "profile": None,
        "MAX_ALLOWED_DEPTH": D,
    }
    input_data = LayerInput(text=text, tokens=tokens, metadata=metadata)

    for layer_id, layer_module in LAYERS:
        input_data.metadata["layers"] = dict(state.layers)
        if layer_id >= 2 and 2 in state.layers:
            input_data.metadata["visited_B"] = set(state.layers[2].get("VISITED_IDS", []))
        if layer_id == 7:
            stability_out = run_stability(state.layers)
            state.diagnostics["stability"] = stability_out
            input_data.metadata["stability"] = stability_out
        output = layer_module.run(input_data)
        state.layers[layer_id] = output.result
        state.diagnostics[str(layer_id)] = output.diagnostics

    assert "stability" in state.diagnostics
    stability = state.diagnostics["stability"]
    assert "anomaly_score" in stability and "instability_flags" in stability
    L7 = state.layers[7]
    if stability["anomaly_score"] > ANOMALY_SCORE_THRESHOLD_LOW_CONFIDENCE:
        assert L7.get("OUTPUT_TRUST_TAG") == "LOW_CONFIDENCE"
        assert "STABILITY_ANOMALY_SCORE" in L7
    else:
        assert "OUTPUT_TRUST_TAG" in L7
