# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3.x — adversarial test batch.
Try to break the guard pipeline: extreme traversal, oscillating area hops,
zero evidence flood, corrupted output injection. If it survives → then we expand.
"""

from __future__ import annotations

import random

try:
    from core.propagation.guard_pipeline import run_pipeline, is_degraded
    from core.propagation.invariant_enforcer import enforce as sigma_enforce
    from core.propagation.theta_gate import G_DEGRADED_MAX
except ImportError:
    from guard_pipeline import run_pipeline, is_degraded
    from invariant_enforcer import enforce as sigma_enforce
    from theta_gate import G_DEGRADED_MAX


def _six_key(g: float, l: float, t: float, o: float):
    return {
        "governance": g,
        "loopability": l,
        "tension_energy": t,
        "obstacle_score": o,
        "dominant_family": None,
        "dominant_area": None,
    }


# ---------- Extreme traversal length ----------
def test_extreme_traversal_length():
    result = _six_key(0.9, 0.5, 0.1, 0.1)
    out = run_pipeline(result, traversal_length=10_000, area_hop_count=0, evidence_count=5)
    assert set(out.keys()) == {"governance", "loopability", "tension_energy", "obstacle_score", "dominant_family", "dominant_area"}
    assert 0 <= out["governance"] <= 1.0
    assert out["governance"] < 0.9


# ---------- Oscillating area hops ----------
def test_oscillating_area_hops():
    result = _six_key(0.8, 0.6, 0.2, 0.2)
    for ah in (0, 5, 0, 10, 3, 8):
        out = run_pipeline(result, traversal_length=5, area_hop_count=ah, evidence_count=3)
        assert 0 <= out["governance"] <= 1.0
        assert 0 <= out["loopability"] <= 1.0


# ---------- Zero evidence flood ----------
def test_zero_evidence_flood():
    result = _six_key(0.85, 0.2, 0.15, 0.2)
    out = run_pipeline(result, traversal_length=0, area_hop_count=0, evidence_count=0)
    assert out["governance"] <= G_DEGRADED_MAX
    assert 0 <= out["governance"] <= 1.0


# ---------- Random corrupted output injection (must hard stop) ----------
def test_corrupted_extra_key_rejected():
    result = _six_key(0.8, 0.5, 0.2, 0.2)
    result["evil_key"] = "injected"
    try:
        run_pipeline(result, 0, 0, 1)
        raise AssertionError("expected Sigma HARD_STOP for extra key")
    except RuntimeError as e:
        assert "HARD_STOP" in str(e) or "exactly" in str(e).lower()


def test_corrupted_missing_key_rejected():
    result = _six_key(0.8, 0.5, 0.2, 0.2)
    del result["governance"]
    try:
        run_pipeline(result, 0, 0, 1)
        raise AssertionError("expected Sigma HARD_STOP for missing key")
    except RuntimeError as e:
        assert "HARD_STOP" in str(e) or "missing" in str(e).lower() or "exactly" in str(e).lower()


def test_corrupted_wrong_type_rejected():
    result = _six_key(0.8, 0.5, 0.2, 0.2)
    result["governance"] = "not a number"
    try:
        run_pipeline(result, 0, 0, 1)
        raise AssertionError("expected Sigma HARD_STOP for wrong type")
    except RuntimeError as e:
        assert "HARD_STOP" in str(e) or "numeric" in str(e).lower()


def test_corrupted_negative_governance_clamped():
    result = _six_key(-0.5, 0.5, 0.2, 0.2)
    out = run_pipeline(result, 0, 0, 1)
    assert out["governance"] >= 0.0


def test_corrupted_governance_above_one_clamped():
    result = _six_key(1.5, 0.5, 0.2, 0.2)
    out = run_pipeline(result, 0, 0, 1)
    assert out["governance"] <= 1.0


# ---------- Stress: many calls with random inputs ----------
def test_stress_random_inputs():
    rng = random.Random(42)
    for _ in range(50):
        g = rng.uniform(0.0, 1.0)
        l = rng.uniform(0.0, 1.0)
        t = max(0.0, rng.gauss(0.2, 0.2))
        o = max(0.0, rng.gauss(0.2, 0.2))
        result = _six_key(g, l, t, o)
        tra = rng.randint(0, 100)
        hop = rng.randint(0, 20)
        ev = rng.randint(0, 10)
        out = run_pipeline(result, traversal_length=tra, area_hop_count=hop, evidence_count=ev)
        assert 0 <= out["governance"] <= 1.0
        assert 0 <= out["loopability"] <= 1.0
        assert out["tension_energy"] >= 0
        assert out["obstacle_score"] >= 0
