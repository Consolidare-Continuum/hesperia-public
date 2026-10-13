# HESPERIA — RAD. Hex product output engine.

from __future__ import annotations

import numpy as np

from core.engine.hex_outputs.hex_output_engine import (
    HexOutputParams,
    attach_hex_product_outputs,
    attach_microstructure_analytics_public,
    compute_hex_outputs,
)


def _triangle_adjacency():
    # 0—1—2 triangle + 0—2
    return [[1, 2], [0, 2], [0, 1]]


def test_hotspot_and_front():
    a = np.array([1.0, 0.5, 0.0])
    adj = _triangle_adjacency()
    c = np.ones((3, 3)) * 0.1
    np.fill_diagonal(c, 0.0)
    r = np.array([0.1, 0.1, 0.1])
    fam = {0: [0], 1: [1], 2: [2]}
    d = np.array([[0, 1, 1], [1, 0, 1], [1, 1, 0]], dtype=np.float64)
    out = compute_hex_outputs(a, adj, c, r, fam, {0: 1.0, 1: 0.5, 2: 0.0}, d)
    assert out["hex_hotspot_map"][0] > a[0]
    assert out["hex_contradiction_front"][0] >= 0
    assert len(out["propagation_corridors"]["corridor_edges"]) >= 1
    assert out["family_multiscale_consistency"][0] == 1.0


def test_attach_from_hits():
    h = [0] * 288
    h[5] = 3
    h[10] = 2
    pub = attach_microstructure_analytics_public(h, F=288)
    assert pub["engine"] == "hex_product_outputs_v1"
    assert "microstructure_hotspots" in pub
    assert len(pub["microstructure_hotspots"]) == pub["active_slot_count"]
    assert 5 in pub["active_policy_families"] or 10 in pub["active_policy_families"]


def test_serialize_roundtrip_keys():
    h = [0] * 288
    h[1] = 5
    raw = attach_hex_product_outputs(h, F=288, max_families=4, nh_per_family=5)
    assert "hex_hotspot_map" in raw
    assert isinstance(raw["hex_hotspot_map"], list)
