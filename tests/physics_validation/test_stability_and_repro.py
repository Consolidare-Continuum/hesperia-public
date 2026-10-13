# A) Stability + E) Reproducibility

from __future__ import annotations

import numpy as np

from core.engine.energy import EnergyControlParams, EnergyMode
from hesperia.extensions.dynamics.equations import (
    SemanticFieldParams,
    build_contradiction_matrix,
    build_family_laplacian,
    build_resistance_matrix,
    run_until_convergence,
)


def test_family_field_converges_strict_energy(repo_root, validation_thresholds):
    max_steps = int(validation_thresholds["stability"]["max_steps_family_field"])
    ec = EnergyControlParams(mode=EnergyMode.strict)
    p = SemanticFieldParams(
        alpha=0.08,
        beta=0.04,
        gamma=0.06,
        delta=0.2,
        dt=0.04,
        epsilon=1e-3,
        tau=1e-2,
        clip_mode=True,
    )
    rng = np.random.RandomState(0)
    f0 = rng.rand(5).astype(np.float64) * 0.2
    s = np.ones(5, dtype=np.float64) * 0.15
    l = build_family_laplacian(np.ones((5, 5)) - np.eye(5))
    r = build_resistance_matrix([0.1] * 5)
    c = build_contradiction_matrix(np.ones((5, 5)) - np.eye(5))
    out = run_until_convergence(f0, s, l, r, c, p, max_steps=max_steps, energy_control=ec)
    assert len(out.energy_trace) >= 2
    for a, b in zip(out.energy_trace, out.energy_trace[1:]):
        assert b <= a + 1e-7


def test_reproducible_family_trajectory():
    p = SemanticFieldParams(
        alpha=0.05,
        beta=0.02,
        gamma=0.04,
        delta=0.15,
        dt=0.03,
        epsilon=1e-9,
        tau=1e-9,
        clip_mode=True,
    )
    f0 = np.array([0.1, 0.2, 0.15, 0.05], dtype=np.float64)
    s = np.array([0.4, 0.1, 0.2, 0.1], dtype=np.float64)
    l = build_family_laplacian([[0.0, 1.0, 0.0, 0.0], [1.0, 0.0, 1.0, 0.0], [0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0, 0.0]])
    r = build_resistance_matrix([0.12, 0.12, 0.12, 0.12])
    c = build_contradiction_matrix([[0.0, 0.2, 0.0, 0.0], [0.2, 0.0, 0.2, 0.0], [0.0, 0.2, 0.0, 0.2], [0.0, 0.0, 0.2, 0.0]])
    o1 = run_until_convergence(f0, s, l, r, c, p, max_steps=20)
    o2 = run_until_convergence(f0, s, l, r, c, p, max_steps=20)
    assert np.allclose(o1.field_final, o2.field_final, atol=0.0, rtol=0.0)
