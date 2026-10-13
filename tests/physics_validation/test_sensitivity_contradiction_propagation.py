# B) Sensitivity, C) Contradiction, D) Propagation

from __future__ import annotations

import numpy as np

from core.engine.product_signals import compute_product_signals
from hesperia.extensions.dynamics.equations import (
    SemanticFieldParams,
    build_contradiction_matrix,
    build_family_laplacian,
    build_resistance_matrix,
    run_until_convergence,
)


def test_sensitivity_small_input_change(validation_thresholds):
    min_rel = float(validation_thresholds["sensitivity"]["min_relative_change_outputs"])
    p = SemanticFieldParams(
        alpha=0.06,
        beta=0.03,
        gamma=0.05,
        delta=0.18,
        dt=0.025,
        epsilon=1e-9,
        tau=1e-9,
        clip_mode=True,
    )
    n = 4
    l = build_family_laplacian(np.ones((n, n)) - np.eye(n))
    r = build_resistance_matrix([0.1] * n)
    c = build_contradiction_matrix(np.ones((n, n)) - np.eye(n))
    f0 = np.zeros(n, dtype=np.float64)
    s0 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    eps = float(validation_thresholds["sensitivity"]["perturbation_scale"])
    s1 = np.array([1.0 + eps, 0.0, 0.0, 0.0], dtype=np.float64)
    o0 = run_until_convergence(f0, s0, l, r, c, p, max_steps=30)
    o1 = run_until_convergence(f0, s1, l, r, c, p, max_steps=30)
    diff = float(np.linalg.norm(o0.field_final - o1.field_final, ord=np.inf))
    base = float(np.linalg.norm(o0.field_final, ord=np.inf)) + 1e-9
    assert diff / base >= min_rel


def test_contradiction_pressure_rises_with_conflict(validation_thresholds):
    thr = float(validation_thresholds["contradiction"]["min_contradiction_pressure_conflict_fixture"])
    nf, nh = 6, 16
    rng = np.random.RandomState(3)
    a0 = rng.rand(nf, nh) * 0.04
    a1 = a0.copy()
    # Two families high — cross-terms in Gram-style contradiction
    a1[0, :] += 0.35
    a1[1, :] += 0.35
    c = np.zeros((nf, nf), dtype=np.float64)
    c[0, 1] = c[1, 0] = 0.8
    s0 = compute_product_signals(a0, a0, C_F=c, dt=1.0)
    s1 = compute_product_signals(a1, a1, C_F=c, dt=1.0)
    assert float(s1["contradiction_pressure"]) > float(s0["contradiction_pressure"]) + thr


def test_propagation_localized_input_spreads_hex_entropy(validation_thresholds):
    thr = float(validation_thresholds["propagation"]["min_hex_entropy_spread_fixture"])
    nf, nh = 8, 32

    def _row_entropy(row: np.ndarray) -> float:
        r = np.asarray(row, dtype=np.float64)
        s = float(r.sum()) + 1e-15
        p = r[r > 0] / s
        return float(-np.sum(p * np.log(p + 1e-15)))

    a0 = np.zeros((nf, nh), dtype=np.float64)
    a0[2, 5] = 1.0
    a1 = np.zeros((nf, nh), dtype=np.float64)
    a1[2, :] = 1.0 / nh
    h0 = _row_entropy(a0[2])
    h1 = _row_entropy(a1[2])
    assert h1 > h0 + thr
