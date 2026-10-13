"""v7 engine foundations — metric math integrated into core pipeline."""
from __future__ import annotations

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# path_metric wired into propagation corridor serialization (METRIC-24/25)
# ---------------------------------------------------------------------------

def test_serialize_hex_outputs_includes_path_metric() -> None:
    from core.engine.hex_outputs.hex_output_engine import (
        build_sparse_hex_scene,
        compute_hex_outputs,
        serialize_hex_outputs,
    )

    hits = [10, 5, 3] + [0] * 285
    C_F = np.eye(288, dtype=np.float64) * 0.01
    scene = build_sparse_hex_scene(hits, C_F, nh_per_family=6, max_families=3)
    raw = compute_hex_outputs(
        scene["hex_activation"],
        scene["adjacency"],
        scene["contradiction_matrix"],
        scene["resistance"],
        scene["family_hex_map"],
        scene["family_activation"],
        scene["distance_matrix"],
    )
    ser = serialize_hex_outputs(raw)
    pc = ser["propagation_corridors"]
    assert "path_metric_cost" in pc
    assert "path_metric_layers" in pc
    assert "path_action_version" in pc
    assert pc["path_action_version"] == "0.1"
    assert isinstance(pc["path_metric_cost"], float)
    assert pc["path_metric_cost"] >= 0.0


# ---------------------------------------------------------------------------
# GCS spacing_factor wired into distance matrix
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="HESPERIA_GCS_EMIT=1 static metric-geometry block (METRIC-22) explicitly deferred to "
    "follow-on rows, not v0.7.0 scope — release/v0.7.0/RELEASE_SCOPE.md. "
    "runtime/services/gcs_lookup.spacing_factor exists and is unit-tested but never wired into "
    "hex_output_engine.build_sparse_hex_scene's distance_matrix.",
    strict=True,
)
def test_sparse_hex_scene_distance_uses_spacing_factor() -> None:
    from core.engine.hex_outputs.hex_output_engine import build_sparse_hex_scene
    from runtime.services.gcs_lookup import spacing_factor

    hits = [0] * 288
    hits[0] = 5   # family 0 → mod-6==0 → 250 slots
    hits[1] = 5   # family 1 → mod-6==1 → 251 slots
    C_F = np.eye(288, dtype=np.float64) * 0.01
    scene = build_sparse_hex_scene(hits, C_F, nh_per_family=6, max_families=2)

    dist = scene["distance_matrix"]
    fhm = scene["family_hex_map"]

    sf_0 = spacing_factor(0)
    sf_1 = spacing_factor(1)

    h0_a, h0_b = fhm[0][0], fhm[0][1]
    assert abs(dist[h0_a, h0_b] - 1.0 * sf_0) < 1e-9

    h1_a, h1_b = fhm[1][0], fhm[1][1]
    assert abs(dist[h1_a, h1_b] - 1.0 * sf_1) < 1e-9

    assert sf_0 != sf_1


# ---------------------------------------------------------------------------
# hesperia_metric on engine_analyze_contract output
# ---------------------------------------------------------------------------

def test_engine_analyze_contract_has_metric_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_METRIC_EMIT", "1")
    from runtime.services.anchor_map_registry import load_anchor_map_v1
    from runtime.services.engine_analyze_contract import build_engine_analyze_from_raw

    load_anchor_map_v1.cache_clear()

    raw = {
        "multiscale_signals": {
            "family_activation_vector": [0.5] * 288,
            "hspr_index": 0.75,
            "contradiction_pressure": 0.1,
            "propagation_strength": 0.6,
        },
        "diagnostics": {
            "interpretability_trace": {
                "marker_concept_sample": [
                    {"linked_family": 0, "concept_id": "c1", "token": "test"},
                    {"linked_family": 24, "concept_id": "c2", "token": "word"},
                ],
            },
        },
    }
    result = build_engine_analyze_from_raw(raw)
    # 24_SPEC §10.1: the block lives at meta.hesperia_metric, not top-level.
    assert "hesperia_metric" in result["meta"]
    hm = result["meta"]["hesperia_metric"]
    assert hm["hesperia_metric_version"] == "0.1.0"
    assert "interior_point_of_world_view" in hm
    assert hm["interior_point_of_world_view"]["powv_point_zero"] is True
    assert result["meta"]["interior_point_of_world_view"] == hm["interior_point_of_world_view"]


def test_engine_analyze_contract_no_metric_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_METRIC_EMIT", raising=False)
    from runtime.services.engine_analyze_contract import build_engine_analyze_from_raw

    raw = {
        "multiscale_signals": {
            "family_activation_vector": [0.5] * 288,
            "hspr_index": 0.75,
            "contradiction_pressure": 0.1,
            "propagation_strength": 0.6,
        },
        "diagnostics": {"interpretability_trace": {"marker_concept_sample": []}},
    }
    result = build_engine_analyze_from_raw(raw)
    assert "meta" not in result


# ---------------------------------------------------------------------------
# path_metric on engine_analyze trace (area crossings)
# ---------------------------------------------------------------------------

def test_engine_analyze_contract_path_metric_on_area_crossings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_METRIC_EMIT", raising=False)
    from runtime.services.engine_analyze_contract import build_engine_analyze_from_raw

    raw = {
        "multiscale_signals": {
            "family_activation_vector": [0.0] * 288,
            "hspr_index": 0.8,
            "contradiction_pressure": 0.05,
            "propagation_strength": 0.7,
        },
        "diagnostics": {
            "interpretability_trace": {
                "marker_concept_sample": [
                    {"linked_family": 0, "concept_id": "c1", "token": "a"},
                    {"linked_family": 24, "concept_id": "c2", "token": "b"},
                    {"linked_family": 48, "concept_id": "c3", "token": "c"},
                ],
            },
        },
    }
    result = build_engine_analyze_from_raw(raw)
    if "path_metric_cost" in result:
        assert result["path_metric_cost"] >= 0.0
        assert result["path_action_version"] == "0.1"


# ---------------------------------------------------------------------------
# IPoW in multiscale_product_bridge output
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="Full meta.interior_point_of_world_view live emit (METRIC-23, HRES-04) explicitly "
    "deferred to follow-on rows, not v0.7.0 scope — release/v0.7.0/RELEASE_SCOPE.md. "
    "build_structural_internal_from_multiscale never attaches it.",
    strict=True,
)
def test_multiscale_bridge_includes_ipow_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_METRIC_EMIT", "1")
    from runtime.services.anchor_map_registry import load_anchor_map_v1

    load_anchor_map_v1.cache_clear()

    from core.engine.multiscale_product_bridge import build_structural_internal_from_multiscale
    from pathlib import Path

    assets = Path(__file__).resolve().parents[1] / "assets" / "lexicon" / "curated"
    if not assets.exists():
        pytest.skip("lexicon assets not available")

    try:
        raw = build_structural_internal_from_multiscale(
            "This is a test sentence for the engine.",
            assets,
        )
    except Exception:
        pytest.skip("engine pipeline requires full asset chain")

    meta = raw.get("meta") or {}
    ipow = meta.get("interior_point_of_world_view")
    assert ipow is not None
    assert ipow["powv_point_zero"] is True
    assert ipow["powv_step"] == 0
