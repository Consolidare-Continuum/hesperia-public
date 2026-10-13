# HESPERIA — RAD. Hex microphysics (Option A).

from __future__ import annotations

import numpy as np

from core.engine.hex_dynamics import (
    HexFieldParams,
    canonical_family_field,
    compute_hex_observables,
    family_aggregate_from_hex,
    ring_cluster_compactness,
    run_hex_microphysics,
    run_option_a_hex_primary,
    step_hex_field_euler,
)
from core.engine.hex_matrix_builders import (
    build_ring_laplacian,
    build_uniform_hex_resistance,
    concept_family_weights_to_hex_source,
    family_source_to_hex_uniform,
)


def test_family_aggregate():
    H = np.array([[1.0, 2.0, 0.0], [0.5, 0.5, 0.0]], dtype=np.float64)
    f = family_aggregate_from_hex(H)
    assert np.allclose(f, [3.0, 1.0])
    assert np.allclose(canonical_family_field(H), f)


def test_run_option_a_closure_G_F_unity():
    nf = 5
    inj = np.zeros(nf)
    inj[0] = 2.0
    inj[2] = 1.0
    C = np.zeros((nf, nf))
    C[0, 1] = C[1, 0] = 0.1
    out = run_option_a_hex_primary(
        inj, C, n_steps=8, params=HexFieldParams(gamma_H=0.0, alpha_H=0.1, delta_H=0.3)
    )
    assert out["closure"] == "Option_A_F_equals_P_HF_H"
    assert np.allclose(out["F_canonical"], canonical_family_field(out["H"]))
    assert abs(out["hex_observables_final"].G_F - 1.0) < 1e-9


def test_step_hex_bounded():
    nf, nh = 4, 8
    L = build_ring_laplacian(nh)
    H = np.full((nf, nh), 0.1)
    S = family_source_to_hex_uniform(np.array([1.0, 0.0, 0.0, 0.0]))[:nf, :nh]
    if S.shape[1] != nh:
        S = np.zeros((nf, nh))
        S[:, 0] = 0.25
    R = build_uniform_hex_resistance(nf, nh, 0.5)
    C = np.eye(nf) * 0.01
    np.fill_diagonal(C, 0.0)
    C = C + 0.02
    np.fill_diagonal(C, 0.0)
    p = HexFieldParams(clip_01=True, dt=0.02)
    H1, d = step_hex_field_euler(H, S, L, R, C, p)
    assert H1.shape == H.shape
    assert (H1 >= 0).all() and (H1 <= 1).all()


def test_K_H_equals_S_C_S():
    nf, nh = 3, 5
    H = np.random.RandomState(0).rand(nf, nh) * 0.3
    L = build_ring_laplacian(nh)
    R = build_uniform_hex_resistance(nf, nh, 1.0)
    C = np.array([[0.0, 0.1, 0.2], [0.1, 0.0, 0.05], [0.2, 0.05, 0.0]], dtype=np.float64)
    s = H.sum(axis=1)
    k_expected = float(s @ (C @ s))
    obs = compute_hex_observables(H, L, R, C, 1e-6)
    assert abs(obs.K_H - k_expected) < 1e-9


def test_G_F_unity_when_F_matches():
    nf, nh = 3, 4
    H = np.ones((nf, nh)) * 0.1
    f = family_aggregate_from_hex(H)
    L = build_ring_laplacian(nh)
    R = build_uniform_hex_resistance(nf, nh, 0.1)
    C = np.zeros((nf, nf))
    obs = compute_hex_observables(H, L, R, C, 1e-6, F_external=f)
    assert abs(obs.G_F - 1.0) < 1e-8


def test_ring_compactness_single_cluster():
    h = np.zeros(10)
    h[2:7] = 1.0
    c = ring_cluster_compactness(h, 0.5)
    assert abs(c - 25 / 25) == 0.0


def test_concept_family_to_hex_source():
    wf = np.array([2.0, 0.0, 4.0])
    sh = concept_family_weights_to_hex_source(wf, n_hex_per_family=5)
    assert sh.shape == (3, 5)
    assert np.allclose(sh[0], 0.4)
    assert np.allclose(sh[2], 0.8)


def test_run_hex_microphysics_series():
    nf, nh = 3, 6
    L = build_ring_laplacian(nh)
    H0 = np.zeros((nf, nh))
    H0[0, 0] = 0.2
    S = np.zeros_like(H0)
    S[0, :] = 1.0 / nh
    R = build_uniform_hex_resistance(nf, nh, 0.2)
    C = np.zeros((nf, nf))
    p = HexFieldParams(alpha_H=0.05, beta_H=0.02, gamma_H=0.0, delta_H=0.5, dt=0.1)
    Hf, series = run_hex_microphysics(H0, S, L, R, C, p, n_steps=5)
    assert len(series) == 5
    assert Hf.shape == H0.shape
