# HESPERIA — RAD. Phase 4 L8 cluster gravity.

import pytest

from hesperia.extensions.dynamics.phase4 import (
    apply_cluster_gravity_to_area_injection,
    compute_l8_clusters,
    ephemeral_hex_from_hits,
)
from hesperia.extensions.dynamics.state import Phase4Theta


def test_l8_clusters_consecutive_run():
    hx = {"5": 0.4, "6": 0.3, "7": 0.2}
    clusters, prev = compute_l8_clusters(hx, {}, theta=Phase4Theta())
    assert len(clusters) == 1
    assert clusters[0].cluster_id == "a0_f5_7"
    assert clusters[0].mass == pytest.approx(0.9, rel=1e-5)
    assert "a0_f5_7" in prev


def test_l8_velocity_deterministic():
    hx = {"0": 0.5, "1": 0.5}
    c1, p1 = compute_l8_clusters(hx, {}, theta=Phase4Theta())
    c2, _ = compute_l8_clusters(hx, p1, theta=Phase4Theta())
    assert c2[0].velocity == pytest.approx(0.0, abs=1e-6)


def test_gravity_perturbs_injection():
    clusters, _ = compute_l8_clusters({"10": 0.8, "11": 0.2}, {}, theta=Phase4Theta())
    inj = [1.0 / 12] * 12
    out = apply_cluster_gravity_to_area_injection(inj, clusters, 0.2)
    assert sum(out) == pytest.approx(1.0)
    assert out[0] != inj[0]


def test_ephemeral_hex():
    hits = [0] * 288
    hits[3] = 5
    hits[4] = 3
    e = ephemeral_hex_from_hits(hits, cap=10)
    assert "3" in e
