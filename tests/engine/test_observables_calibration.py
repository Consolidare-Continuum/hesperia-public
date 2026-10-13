# HESPERIA — RAD. Canonical observables + HSPR.

from __future__ import annotations

import numpy as np

from hesperia.engine.calibration import (
    HSPRWeights,
    compute_hspr,
    hspr_from_observables,
    interpret_hspr,
    normalize_observables,
)
from hesperia.extensions.dynamics.semantic_field_v1 import (
    NUM_FAMILIES,
    build_default_matrices,
    load_semantic_field_params_v1,
    source_from_hits_normalized,
    step_field_euler,
)
from core.engine.observables import FieldObservables, compute_field_observables, observables_from_timestep


def test_observables_E_half_L():
    mats = build_default_matrices()
    f = np.full(NUM_FAMILIES, 1.0 / NUM_FAMILIES)
    s = f.copy()
    lf = mats["L_F"] @ f
    E_expected = 0.5 * float(f @ lf)
    obs = compute_field_observables(f, s, mats["L_F"], mats["R_F"], mats["C"])
    assert abs(obs.E - E_expected) < 1e-9
    assert obs.K == float(f @ (mats["C"] @ f))
    assert obs.D == float(np.linalg.norm(lf, ord=2))


def test_observables_sigma_after_step():
    mats = build_default_matrices()
    f0 = np.full(NUM_FAMILIES, 0.5)
    s = source_from_hits_normalized([1] + [0] * (NUM_FAMILIES - 1))
    p = load_semantic_field_params_v1()
    f1, _ = step_field_euler(f0, s, mats["L_F"], mats["R_F"], mats["C"], params=p)
    obs = observables_from_timestep(f0, f1, s, mats["L_F"], mats["R_F"], mats["C"])
    assert obs.Sigma == float(np.linalg.norm(f1 - f0, ord=2))
    assert obs.Sigma > 0


def test_hspr_bounds():
    obs = FieldObservables(E=1.0, K=0.1, R=0.1, D=0.5, Q=2.0, Sigma=0.01)
    hspr, hats = hspr_from_observables(obs)
    assert 0.0 <= hspr <= 1.0
    assert all(0 <= hats[k] <= 1 for k in hats)
    assert interpret_hspr(0.85) == "coherent_narrative"
    assert interpret_hspr(0.1) == "contradiction_dominated"


def test_compute_hspr_extremes():
    w = HSPRWeights(w_sigma=1, w_Q=1, w_E=1, w_K=1, w_R=1, w_D=1)
    best = {"Sigma_hat": 1, "Q_hat": 1, "E_hat": 1, "K_hat": 0, "R_hat": 0, "D_hat": 0}
    worst = {"Sigma_hat": 0, "Q_hat": 0, "E_hat": 0, "K_hat": 1, "R_hat": 1, "D_hat": 1}
    assert abs(compute_hspr(best, w) - 1.0) < 1e-9
    assert abs(compute_hspr(worst, w) - 0.0) < 1e-9


def test_normalize_monotone():
    o1 = FieldObservables(E=0, K=0, R=0, D=0, Q=0, Sigma=0)
    o2 = FieldObservables(E=10, K=10, R=10, D=10, Q=10, Sigma=10)
    h1 = normalize_observables(o1)
    h2 = normalize_observables(o2)
    assert h1["E_hat"] < h2["E_hat"]
    assert h1["Sigma_hat"] > h2["Sigma_hat"]  # smaller step → higher Sigma_hat
