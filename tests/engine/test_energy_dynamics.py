# HESPERIA — RAD. Energy-consistent family + hex dynamics.

from __future__ import annotations

import numpy as np

from core.engine.energy import (
    EnergyControlParams,
    EnergyMode,
    compute_energy_family_1d,
    compute_energy_hex_2d,
)
from core.engine.hex_dynamics import (
    HexFieldParams,
    LocalHexMicrophysicsParams,
    run_hex_microphysics,
    step_hex_field_euler,
    step_hex_local_microphysics,
)
from core.engine.hex_matrix_builders import build_ring_laplacian, build_uniform_hex_resistance
from hesperia.extensions.dynamics.equations import (
    SemanticFieldParams,
    build_contradiction_matrix,
    build_family_laplacian,
    build_resistance_matrix,
    run_until_convergence,
    step_field,
)


def test_compute_energy_family_matches_equations():
    from hesperia.extensions.dynamics.equations import compute_energy

    f = np.array([0.3, 0.7], dtype=np.float64)
    s = np.array([0.5, 0.1], dtype=np.float64)
    l = build_family_laplacian([[0.0, 1.0], [1.0, 0.0]])
    r = build_resistance_matrix([0.2, 0.3])
    c = build_contradiction_matrix([[0.0, 0.4], [0.4, 0.0]])
    p = SemanticFieldParams(alpha=0.2, beta=0.1, gamma=0.15, delta=0.25, dt=0.05)
    e1 = compute_energy(f, s, l, r, c, p)
    e2 = compute_energy_family_1d(f, s, l, r, c, alpha=p.alpha, beta=p.beta, gamma=p.gamma, delta=p.delta)
    assert abs(e1 - e2) < 1e-12


def test_run_until_convergence_energy_trace_length():
    p = SemanticFieldParams(
        alpha=0.05,
        beta=0.02,
        gamma=0.05,
        delta=0.2,
        dt=0.02,
        epsilon=1e-2,
        tau=1e-2,
        clip_mode=True,
    )
    f0 = np.array([0.1, 0.2, 0.15], dtype=np.float64)
    s = np.array([1.0, 0.5, 0.3], dtype=np.float64)
    l = build_family_laplacian(np.ones((3, 3)) - np.eye(3))
    r = build_resistance_matrix([0.1, 0.1, 0.1])
    c = build_contradiction_matrix(np.ones((3, 3)) - np.eye(3))
    out = run_until_convergence(f0, s, l, r, c, p, max_steps=8)
    f_final, timeline = out
    assert len(out.energy_trace) == len(timeline) + 1
    assert f_final.shape == (3,)


def test_strict_energy_family_step_monotone():
    ec = EnergyControlParams(mode=EnergyMode.strict, max_dt_halving_retries=40)
    p = SemanticFieldParams(
        alpha=0.1,
        beta=0.05,
        gamma=0.1,
        delta=0.3,
        dt=2.0,
        epsilon=1e-9,
        tau=1e-9,
        clip_mode=True,
    )
    f = np.array([0.25, 0.75], dtype=np.float64)
    s = np.array([0.4, 0.1], dtype=np.float64)
    l = build_family_laplacian([[0.0, 1.0], [1.0, 0.0]])
    r = build_resistance_matrix([0.1, 0.2])
    c = build_contradiction_matrix([[0.0, 0.5], [0.5, 0.0]])
    r0 = step_field(f, s, l, r, c, p, energy_control=ec)
    assert r0.energy_next <= r0.energy_prev + 1e-10
    assert r0.n_dt_retries >= 0


def test_high_dt_hex_euler_auto_reduces():
    ec = EnergyControlParams(mode=EnergyMode.strict, max_dt_halving_retries=48)
    nf, nh = 3, 8
    H = np.full((nf, nh), 0.05)
    S_H = np.full((nf, nh), 0.1)
    L = build_ring_laplacian(nh)
    R = build_uniform_hex_resistance(nf, nh, 0.3)
    C = np.zeros((nf, nf))
    C[0, 1] = C[1, 0] = 0.05
    p = HexFieldParams(alpha_H=0.1, beta_H=0.05, gamma_H=0.08, delta_H=0.15, dt=5.0, clip_01=True)
    _, d = step_hex_field_euler(H, S_H, L, R, C, p, energy_control=ec, lam_contra=1.0)
    assert d["energy_next"] <= d["energy_prev"] + 1e-9
    assert d["dt_effective"] <= p.dt + 1e-12


def test_hex_microphysics_strict_energy_non_increasing_trace():
    ec = EnergyControlParams(mode=EnergyMode.strict, epsilon_delta_a=1e-12, epsilon_delta_e=1e-12)
    nf, nh = 4, 10
    H0 = np.random.RandomState(1).rand(nf, nh) * 0.08
    S_H = np.full((nf, nh), 0.05)
    L = build_ring_laplacian(nh)
    R = build_uniform_hex_resistance(nf, nh, 0.4)
    C = np.zeros((nf, nf))
    C[0, 1] = C[1, 0] = 0.02
    p = HexFieldParams(
        alpha_H=0.06,
        beta_H=0.04,
        gamma_H=0.05,
        delta_H=0.12,
        dt=0.03,
        clip_01=True,
    )
    out = run_hex_microphysics(H0, S_H, L, R, C, p, n_steps=12, energy_control=ec)
    H, series = out
    assert H.shape == H0.shape
    assert len(series) == 12
    et = out.energy_trace
    assert len(et) == 13
    for a, b in zip(et, et[1:]):
        assert b <= a + 1e-8


def test_hex_local_line_search_soft_energy():
    nf, nh = 3, 12
    rng = np.random.RandomState(2)
    A = rng.rand(nf, nh) * 0.15
    R = np.full((nf, nh), 0.25)
    C = np.zeros((nf, nf))
    C[0, 1] = C[1, 0] = 0.08
    L = build_ring_laplacian(nh)
    s_ref = A.copy()
    ec = EnergyControlParams(mode=EnergyMode.soft, epsilon_energy_soft=1e-3)
    e0 = compute_energy_hex_2d(A, L, C, s_ref, lam_contra=1.0)
    A1 = step_hex_local_microphysics(
        A,
        R,
        C,
        params=LocalHexMicrophysicsParams(alpha=0.06, beta=0.03, gamma=0.04),
        clip_nonneg=True,
        S_H=s_ref,
        L_ring=L,
        energy_control=ec,
    )
    e1 = compute_energy_hex_2d(A1, L, C, s_ref, lam_contra=1.0)
    assert e1 <= e0 + 1e-2


def test_family_step_without_clip_stable_with_energy_control():
    ec = EnergyControlParams(mode=EnergyMode.strict)
    p = SemanticFieldParams(
        alpha=0.08,
        beta=0.04,
        gamma=0.06,
        delta=0.2,
        dt=0.05,
        epsilon=1e-9,
        tau=1e-9,
        clip_mode=False,
    )
    f = np.array([0.2, 0.4], dtype=np.float64)
    s = np.array([0.5, 0.2], dtype=np.float64)
    l = build_family_laplacian([[0.0, 0.5], [0.5, 0.0]])
    r = build_resistance_matrix([0.15, 0.15])
    c = build_contradiction_matrix([[0.0, 0.2], [0.2, 0.0]])
    r0 = step_field(f, s, l, r, c, p, energy_control=ec)
    assert np.all(np.isfinite(r0.field_next))
    assert r0.energy_next <= r0.energy_prev + 1e-10
