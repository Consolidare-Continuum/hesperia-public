# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3.1 — pipeline-level integration tests.
20_SPEC Release v0.3.1 Runtime Guards and Failure Classes.
Stable input → governance unaffected; long traversal → decay; no loopability → sinkage;
extreme instability → degraded; structural violation → hard stop before Gamma;
Gamma before Sigma → incorrect.
"""

from __future__ import annotations

import pytest

try:
    from core.propagation.guard_pipeline import run_pipeline, is_degraded
    from core.propagation.gamma_guard import compute_gamma_penalty
    from core.propagation.theta_gate import apply_theta, G_DEGRADED_MAX, LOOP_DEGRADED_MAX
    from core.propagation.invariant_enforcer import enforce as sigma_enforce
except ImportError:
    from guard_pipeline import run_pipeline, is_degraded
    from gamma_guard import compute_gamma_penalty
    from theta_gate import apply_theta, G_DEGRADED_MAX, LOOP_DEGRADED_MAX
    from invariant_enforcer import enforce as sigma_enforce


def _six_key(governance: float, loopability: float, tension_energy: float, obstacle_score: float):
    return {
        "governance": governance,
        "loopability": loopability,
        "tension_energy": tension_energy,
        "obstacle_score": obstacle_score,
        "dominant_family": None,
        "dominant_area": None,
    }


# ---------- Stable input → governance unaffected ----------
def test_stable_input_governance_unchanged():
    result = _six_key(0.8, 1.0, 0.1, 0.1)
    out = run_pipeline(result, traversal_length=0, area_hop_count=0, evidence_count=5)
    assert out["governance"] == 0.8
    assert out["loopability"] == 1.0


# ---------- Long traversal → governance decays ----------
def test_long_traversal_governance_decays():
    result = _six_key(0.8, 0.5, 0.2, 0.2)
    out = run_pipeline(result, traversal_length=25, area_hop_count=3, evidence_count=5)
    assert out["governance"] < 0.8


# ---------- No loopability → sinkage effect ----------
def test_no_loopability_sinkage():
    result = _six_key(0.7, 0.0, 0.2, 0.2)
    gamma = compute_gamma_penalty(traversal_length=5, area_hop_count=2, loopability=0.0)
    assert gamma > 0
    out = apply_theta(result, gamma, degraded=False)
    assert out["governance"] < 0.7


# ---------- Extreme instability → degraded state ----------
def test_extreme_instability_degraded():
    assert is_degraded(evidence_count=0, gamma_penalty=0.0, loopability=0.5) is True
    assert is_degraded(evidence_count=5, gamma_penalty=0.7, loopability=0.5) is True
    assert is_degraded(evidence_count=5, gamma_penalty=0.3, loopability=0.1) is True
    result = _six_key(0.8, 0.1, 0.2, 0.2)
    out = run_pipeline(result, traversal_length=30, area_hop_count=8, evidence_count=0)
    assert out["governance"] <= G_DEGRADED_MAX  # 0.30
    assert out["tension_energy"] >= 0.2
    assert out["obstacle_score"] >= 0.2


# ---------- Structural violation → hard stop before Gamma ----------
def test_structural_violation_hard_stop_before_gamma():
    bad = _six_key(0.8, 0.5, 0.2, 0.2)
    bad["extra_key"] = 1
    with pytest.raises(RuntimeError, match="Sigma HARD_STOP|exactly"):
        run_pipeline(bad, 0, 0, 1)


# ---------- Gamma runs after Sigma (order: Sigma then Gamma then Theta) ----------
def test_gamma_after_sigma_order():
    # If we ran Gamma before Sigma, we might use unvalidated keys; pipeline runs Sigma first so result has exactly 6 keys
    result = _six_key(0.9, 0.8, 0.0, 0.0)
    out = run_pipeline(result, 10, 2, 3)
    assert set(out.keys()) == {"governance", "loopability", "tension_energy", "obstacle_score", "dominant_family", "dominant_area"}
    assert out["governance"] <= 0.9
