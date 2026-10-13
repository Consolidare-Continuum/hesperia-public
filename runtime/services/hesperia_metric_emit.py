# HESPERIA — HesperiaMetric runtime emit (24_SPEC §10.1 / METRIC-20).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import os
from typing import Any

from runtime.services.anchor_map_registry import frozen_anchor_map_id
from sphere.topology.embedding import coordinate_fingerprint, get_area_coordinates

_TRUTHY = ("1", "true", "yes", "on")


def hesperia_metric_emit_enabled() -> bool:
    return os.environ.get("HESPERIA_METRIC_EMIT", "0").strip() in _TRUTHY


def _gcs_emit_enabled() -> bool:
    return os.environ.get("HESPERIA_GCS_EMIT", "0").strip() in _TRUTHY


def _build_geodesic_sphere_block() -> dict[str, Any]:
    """22_SPEC §9.1 static descriptor — verbatim constants from frozen spec."""
    return {
        "gcs_id": "GCS_NU85_v0_1",
        "nu": 85,
        "hex_face_count": 72240,
        "pentagon_pole_count": 12,
        "total_face_count": 72252,
        "semantic_hex_count": 72000,
        "delta_hex": 240,
        "truth_unit_count_geodesic": 433440,
        "truth_unit_count_semantic": 432000,
        "delta_sides": 1440,
        "gcs_scale_sigma": 1.0033333333,
        "gcs_mean_hex_per_family": 250.8333333333,
        "gcs_mean_hex_per_area": 6020,
        "families_gcs_251": 240,
        "families_gcs_250": 48,
        "extra_hex_per_pentagon_pole": 20,
        "anchor_map_id": frozen_anchor_map_id(),
    }


def _build_point_zero_ipow_block() -> dict[str, Any]:
    """22_SPEC §9.2 / 24_SPEC §14.6 — PointZero read-only snapshot (METRIC-23 + HRES-04)."""
    return {
        "powv_point_zero": True,
        "powv_position": [0.0, 0.0, 0.0],
        "powv_step": 0,
        "powv_distances_tier1": [1.0] * 12,
        "powv_barycentric_areas": [1.0 / 12.0] * 12,
        "iteration_interval_I2": None,
        "delta_powv_norm": 0.0,
    }


def build_hesperia_metric_block() -> dict[str, Any]:
    coords = get_area_coordinates()
    fp = coordinate_fingerprint(coords)
    anchor_map_id = frozen_anchor_map_id()

    layers = ["area_sphere", "hex_graph", "state_gram"]
    if _gcs_emit_enabled():
        layers.append("gcs_surface")

    block: dict[str, Any] = {
        "hesperia_metric_version": "0.1.0",
        "layers_active": layers,
        "area_sphere": {"radius": 1.0, "coordinate_fingerprint": fp},
        "gcs_surface": {"gcs_id": "GCS_NU85_v0_1", "anchor_map_id": anchor_map_id},
        "ipow_volume": {"anchor_map_id": anchor_map_id},
        "anchor_map_id": anchor_map_id,
    }

    if _gcs_emit_enabled():
        block["geodesic_sphere"] = _build_geodesic_sphere_block()

    block["interior_point_of_world_view"] = _build_point_zero_ipow_block()

    return block


def attach_hesperia_metric_meta(payload: dict[str, Any]) -> dict[str, Any]:
    if not hesperia_metric_emit_enabled():
        return payload
    meta = dict(payload.get("meta") or {})
    metric = build_hesperia_metric_block()
    meta["hesperia_metric"] = metric
    # METRIC-23/G10 is a public sibling field, not only an internal metric-registry detail.
    meta["interior_point_of_world_view"] = dict(metric["interior_point_of_world_view"])
    out = dict(payload)
    out["meta"] = meta
    return out
