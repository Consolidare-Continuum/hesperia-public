"""METRIC-22/23/24/26 + HRES-04 — geodesic_sphere, IPoW PointZero, path_metric, gcs_lookup."""
from __future__ import annotations

import math

import pytest


# ---------------------------------------------------------------------------
# METRIC-22: HESPERIA_GCS_EMIT=1 → geodesic_sphere block
# ---------------------------------------------------------------------------

def test_geodesic_sphere_absent_without_gcs_emit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_GCS_EMIT", raising=False)
    from runtime.services.anchor_map_registry import load_anchor_map_v1
    from runtime.services.hesperia_metric_emit import build_hesperia_metric_block

    load_anchor_map_v1.cache_clear()
    block = build_hesperia_metric_block()
    assert "geodesic_sphere" not in block
    assert "gcs_surface" not in block["layers_active"]


def test_geodesic_sphere_present_with_gcs_emit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HESPERIA_GCS_EMIT", "1")
    from runtime.services.anchor_map_registry import load_anchor_map_v1
    from runtime.services.hesperia_metric_emit import build_hesperia_metric_block

    load_anchor_map_v1.cache_clear()
    block = build_hesperia_metric_block()
    gs = block["geodesic_sphere"]
    assert gs["gcs_id"] == "GCS_NU85_v0_1"
    assert gs["nu"] == 85
    assert gs["hex_face_count"] == 72240
    assert gs["pentagon_pole_count"] == 12
    assert gs["total_face_count"] == 72252
    assert gs["semantic_hex_count"] == 72000
    assert gs["delta_hex"] == 240
    assert gs["anchor_map_id"] == "anchor_map_v1"
    assert "gcs_surface" in block["layers_active"]


# ---------------------------------------------------------------------------
# METRIC-23 + HRES-04: interior_point_of_world_view PointZero
# ---------------------------------------------------------------------------

def test_ipow_point_zero_on_metric_block(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HESPERIA_GCS_EMIT", raising=False)
    from runtime.services.anchor_map_registry import load_anchor_map_v1
    from runtime.services.hesperia_metric_emit import build_hesperia_metric_block

    load_anchor_map_v1.cache_clear()
    block = build_hesperia_metric_block()
    ipow = block["interior_point_of_world_view"]

    assert ipow["powv_point_zero"] is True
    assert ipow["powv_position"] == [0.0, 0.0, 0.0]
    assert ipow["powv_step"] == 0
    assert len(ipow["powv_distances_tier1"]) == 12
    assert all(d == 1.0 for d in ipow["powv_distances_tier1"])
    assert len(ipow["powv_barycentric_areas"]) == 12
    assert abs(sum(ipow["powv_barycentric_areas"]) - 1.0) < 1e-9
    assert ipow["iteration_interval_I2"] is None
    assert ipow["delta_powv_norm"] == 0.0


# ---------------------------------------------------------------------------
# METRIC-24: path_metric_cost + S_path
# ---------------------------------------------------------------------------

def test_compute_s_path_empty() -> None:
    from runtime.services.path_metric import compute_s_path

    result = compute_s_path([])
    assert result["path_metric_cost"] == 0.0
    assert result["path_metric_layers"] == []
    assert result["path_action_version"] == "0.1"


def test_compute_s_path_area_sphere_edges() -> None:
    from runtime.services.path_metric import compute_s_path

    edges = [
        {"layer": "area_sphere", "geodesic_distance": 0.5},
        {"layer": "area_sphere", "geodesic_distance": 1.2},
    ]
    result = compute_s_path(edges)
    assert abs(result["path_metric_cost"] - 1.7) < 1e-6
    assert result["path_metric_layers"] == ["area_sphere"]


def test_compute_s_path_concept_graph_edge() -> None:
    from runtime.services.path_metric import compute_s_path

    edges = [{"layer": "concept_graph", "weight": 0.5}]
    result = compute_s_path(edges)
    expected = -math.log(0.5)
    assert abs(result["path_metric_cost"] - expected) < 1e-6


def test_compute_s_path_mixed_layers() -> None:
    from runtime.services.path_metric import compute_s_path

    edges = [
        {"layer": "area_sphere", "geodesic_distance": 1.0},
        {"layer": "hex_graph", "gradient": 0.3},
    ]
    result = compute_s_path(edges)
    assert abs(result["path_metric_cost"] - 1.3) < 1e-6
    assert result["path_metric_layers"] == ["area_sphere", "hex_graph"]


def test_attach_path_metric_noop_on_none() -> None:
    from runtime.services.path_metric import attach_path_metric

    payload = {"key": "value"}
    assert attach_path_metric(payload, None) is payload
    assert attach_path_metric(payload, []) is payload


def test_attach_path_metric_adds_fields() -> None:
    from runtime.services.path_metric import attach_path_metric

    payload = {"data": 123}
    edges = [{"layer": "hex_graph", "gradient": 2.0}]
    result = attach_path_metric(payload, edges)
    assert result["data"] == 123
    assert "path_metric_cost" in result
    assert result["path_action_version"] == "0.1"


# ---------------------------------------------------------------------------
# METRIC-26: gcs_lookup — spacing_factor + J_sem→gcs
# ---------------------------------------------------------------------------

def test_spacing_factor_mod6_families() -> None:
    from runtime.services.gcs_lookup import spacing_factor

    sf_250 = spacing_factor(0)
    sf_251 = spacing_factor(1)
    gcs_mean = 72240.0 / 288
    assert abs(sf_250 - 250 / gcs_mean) < 1e-9
    assert abs(sf_251 - 251 / gcs_mean) < 1e-9
    assert sf_250 < sf_251


def test_family_slot_counts_match_anchor_map() -> None:
    from runtime.services.gcs_lookup import _family_gcs_slot_count, TOTAL_FAMILIES

    count_250 = sum(1 for f in range(TOTAL_FAMILIES) if _family_gcs_slot_count(f) == 250)
    count_251 = sum(1 for f in range(TOTAL_FAMILIES) if _family_gcs_slot_count(f) == 251)
    assert count_250 == 48
    assert count_251 == 240
    total_gcs = count_250 * 250 + count_251 * 251
    assert total_gcs == 72240


def test_sem_to_gcs_range() -> None:
    from runtime.services.gcs_lookup import sem_to_gcs

    assert sem_to_gcs(0) == 0
    last = sem_to_gcs(71999)
    assert last < 72240


def test_sem_to_gcs_out_of_range() -> None:
    from runtime.services.gcs_lookup import sem_to_gcs

    with pytest.raises(IndexError):
        sem_to_gcs(72000)
    with pytest.raises(IndexError):
        sem_to_gcs(-1)


def test_gcs_extra_indices_count() -> None:
    from runtime.services.gcs_lookup import gcs_extra_indices

    extras = gcs_extra_indices()
    assert len(extras) == 240
