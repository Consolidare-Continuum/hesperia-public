# HESPERIA — RAD. Ethan Phase 2 — L5 family (H4, H5) + coupled L6 injection.
# specs/dynamics/ETHAN_SEMANTIC_FIELD_DYNAMICS_SPEC.md §A.6 Phase 2.

from __future__ import annotations

from typing import Sequence

import numpy as np

from hesperia.extensions.dynamics.phase1 import step_phase1
from hesperia.extensions.dynamics.state import (
    FAMILIES_PER_AREA,
    NUM_AREAS,
    NUM_FAMILIES,
    FieldDynamicsState,
    Phase1Theta,
    Phase2Theta,
)


def _normalize_l1_12(v: np.ndarray) -> np.ndarray:
    v = np.maximum(np.asarray(v, dtype=np.float64).reshape(NUM_AREAS), 0.0)
    s = float(v.sum())
    if s <= 0.0:
        return np.full(NUM_AREAS, 1.0 / NUM_AREAS, dtype=np.float64)
    return v / s


def _normalize_l1_288(v: np.ndarray) -> np.ndarray:
    v = np.maximum(np.asarray(v, dtype=np.float64).reshape(NUM_FAMILIES), 0.0)
    s = float(v.sum())
    if s <= 0.0:
        return np.full(NUM_FAMILIES, 1.0 / NUM_FAMILIES, dtype=np.float64)
    return v / s


def step_phase2(
    state: FieldDynamicsState,
    hit_area_injection: Sequence[float],
    family_hit_injection: Sequence[float],
    *,
    contradiction_signal_area: Sequence[float] | None = None,
    theta1: Phase1Theta | None = None,
    theta2: Phase2Theta | None = None,
) -> FieldDynamicsState:
    """
    L5: update f_f (H4-style) and p_family (H5); build hat F_a per area;
    L6: blend hit-area vs family-aggregate injection, then Phase 1 area step.
    """
    th1 = theta1 or Phase1Theta()
    th2 = theta2 or Phase2Theta()
    f_f = np.asarray(state.f_f, dtype=np.float64).copy()
    p_fam = np.asarray(state.p_family, dtype=np.float64).copy()
    x_hat = _normalize_l1_288(np.asarray(list(family_hit_injection), dtype=np.float64))

    area_mean = np.zeros(NUM_FAMILIES, dtype=np.float64)
    for a in range(NUM_AREAS):
        sl = slice(FAMILIES_PER_AREA * a, FAMILIES_PER_AREA * (a + 1))
        area_mean[sl] = float(f_f[sl].mean())
    a_broadcast = np.repeat(state.area_a, FAMILIES_PER_AREA)

    f_raw = (
        (1.0 - th2.lambda_f) * f_f
        + th2.beta_x * x_hat
        + th2.beta_intra * (area_mean - f_f)
        + th2.beta_area * a_broadcast
        - th2.beta_pf * p_fam
    )
    f_new = np.clip(f_raw, 0.0, None)
    f_new = _normalize_l1_288(f_new)

    sig = (
        np.maximum(
            np.asarray(list(contradiction_signal_area), dtype=np.float64).reshape(NUM_AREAS),
            0.0,
        )
        if contradiction_signal_area is not None
        else np.zeros(NUM_AREAS, dtype=np.float64)
    )
    sig_f = np.zeros(NUM_FAMILIES, dtype=np.float64)
    for a in range(NUM_AREAS):
        sl = slice(FAMILIES_PER_AREA * a, FAMILIES_PER_AREA * (a + 1))
        sig_f[sl] = sig[a] / float(FAMILIES_PER_AREA)
    p_fam = (1.0 - th2.mu_f) * p_fam + th2.delta_f * sig_f - th2.rho_f
    p_fam = np.maximum(p_fam, 0.0)

    hat_F = np.array([float(f_new[FAMILIES_PER_AREA * a : FAMILIES_PER_AREA * (a + 1)].sum()) for a in range(NUM_AREAS)])
    hat_F_n = _normalize_l1_12(hat_F)
    hit_12 = _normalize_l1_12(np.asarray(list(hit_area_injection), dtype=np.float64))
    w = float(np.clip(th2.area_hit_weight, 0.0, 1.0))
    inj_12 = w * hit_12 + (1.0 - w) * hat_F_n
    inj_12 = _normalize_l1_12(inj_12)

    mid = FieldDynamicsState(
        t=state.t,
        area_a=state.area_a.copy(),
        p_a=state.p_a.copy(),
        stab=state.stab,
        concept_mass=state.concept_mass,
        f_f=f_new,
        p_family=p_fam,
        hex_x=dict(state.hex_x),
        hex_p=dict(state.hex_p),
        l8_cluster_mass_prev=dict(getattr(state, "l8_cluster_mass_prev", {}) or {}),
        version=4,
    )
    out = step_phase1(mid, inj_12, contradiction_signal=contradiction_signal_area, theta=th1)
    return FieldDynamicsState(
        t=out.t,
        area_a=out.area_a,
        p_a=out.p_a,
        stab=out.stab,
        concept_mass=out.concept_mass,
        f_f=f_new,
        p_family=p_fam,
        hex_x=dict(out.hex_x),
        hex_p=dict(out.hex_p),
        l8_cluster_mass_prev=dict(getattr(out, "l8_cluster_mass_prev", {}) or {}),
        version=4,
    )


def field_dynamics_phase2_enabled() -> bool:
    import os

    return os.environ.get("HESPERIA_FIELD_DYNAMICS_PHASE2", "").strip().lower() in ("1", "true", "yes")
