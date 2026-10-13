# HESPERIA — RAD. Ethan Phase 1 — L0+L2 stub + L6+L7+L9 minimal step.
# Canonical: specs/dynamics/ETHAN_SEMANTIC_FIELD_DYNAMICS_SPEC.md §A.6 Phase 1.
# Opt-in only; does not alter default pipeline.

from __future__ import annotations

from typing import Sequence

import numpy as np

from hesperia.extensions.dynamics.state import NUM_AREAS, NUM_FAMILIES, FieldDynamicsState, Phase1Theta
from sphere.topology.topology_loader import get_icosahedral_adjacency


def _normalize_l1(v: np.ndarray) -> np.ndarray:
    v = np.maximum(np.asarray(v, dtype=np.float64).reshape(NUM_AREAS), 0.0)
    s = float(v.sum())
    if s <= 0.0:
        return np.full(NUM_AREAS, 1.0 / NUM_AREAS, dtype=np.float64)
    return v / s


def step_phase1(
    state: FieldDynamicsState,
    injection: Sequence[float],
    *,
    contradiction_signal: Sequence[float] | None = None,
    theta: Phase1Theta | None = None,
) -> FieldDynamicsState:
    """
    One dynamics step: inject normalized area snapshot, diffuse on icosahedron,
    update area contradiction pressure, stability (compact H9-style).

    injection: length-12 non-negative (e.g. hit-normalized area vector from a run).
    contradiction_signal: optional per-area drive for p_a (e.g. TRIZ-derived later).
    """
    th = theta or Phase1Theta()
    inj = _normalize_l1(np.asarray(list(injection), dtype=np.float64))
    sig = (
        np.maximum(np.asarray(list(contradiction_signal), dtype=np.float64).reshape(NUM_AREAS), 0.0)
        if contradiction_signal is not None
        else np.zeros(NUM_AREAS, dtype=np.float64)
    )

    adj = get_icosahedral_adjacency().astype(np.float64)
    deg = adj.sum(axis=1)
    neighbor_avg = (adj @ state.area_a) / np.maximum(deg, 1.0)

    a_prev = state.area_a.copy()
    raw = (
        (1.0 - th.lambda_a) * state.area_a
        + th.gamma_f * inj
        + th.gamma_q * neighbor_avg
        - th.gamma_p * state.p_a
    )
    a_new = np.clip(raw, 0.0, 1.0)
    a_new = _normalize_l1(a_new)

    p_new = (1.0 - th.mu_a) * state.p_a + th.delta_a * sig - th.rho_a
    p_new = np.maximum(p_new, 0.0)

    stab = 1.0 - float(np.mean(np.abs(a_new - a_prev)))

    c_new = (1.0 - th.lambda_c) * state.concept_mass + th.alpha_in * float(inj.sum())

    return FieldDynamicsState(
        t=state.t + 1,
        area_a=a_new,
        p_a=p_new,
        stab=stab,
        concept_mass=c_new,
        f_f=np.asarray(state.f_f, dtype=np.float64).reshape(NUM_FAMILIES).copy(),
        p_family=np.asarray(state.p_family, dtype=np.float64).reshape(NUM_FAMILIES).copy(),
        hex_x=dict(state.hex_x),
        hex_p=dict(state.hex_p),
        l8_cluster_mass_prev=dict(getattr(state, "l8_cluster_mass_prev", {}) or {}),
        version=max(int(getattr(state, "version", 1)), 4),
    )


def field_dynamics_enabled() -> bool:
    import os

    return os.environ.get("HESPERIA_FIELD_DYNAMICS", "").strip().lower() in ("1", "true", "yes")
