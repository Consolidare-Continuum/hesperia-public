# HESPERIA — RAD. Ethan Phase 3 — L4 active subgraph (family-proxy cells, capped).
# specs/dynamics/ETHAN_SEMANTIC_FIELD_DYNAMICS_SPEC.md §A.6 Phase 3, Part B §9.

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

import numpy as np

from hesperia.extensions.dynamics.state import (
    FAMILIES_PER_AREA,
    NUM_AREAS,
    NUM_FAMILIES,
    FieldDynamicsState,
    Phase3Theta,
)


def step_phase3(
    state: FieldDynamicsState,
    hits: Sequence[int],
    contradiction_signal_area: Sequence[float],
    *,
    theta: Phase3Theta | None = None,
) -> FieldDynamicsState:
    """
    Update sparse hex_x / hex_p on **active** families (proxy lattice cells).
    Neighbors: consecutive active families within same area (induced 1-D chain per area).
    Does not increment t — run before Phase 2/1 in the same tick.
    """
    th = theta or Phase3Theta()
    cap = max(1, min(int(th.hex_cap), NUM_FAMILIES))
    h = list(hits)[:NUM_FAMILIES]
    while len(h) < NUM_FAMILIES:
        h.append(0)
    total = float(sum(h))
    hitn = np.array([x / total if total > 0 else 1.0 / NUM_FAMILIES for x in h], dtype=np.float64)
    sig = np.maximum(np.asarray(list(contradiction_signal_area), dtype=np.float64).reshape(NUM_AREAS), 0.0)

    order = sorted(range(NUM_FAMILIES), key=lambda f: (-h[f], f))
    active = [f for f in order if h[f] > 0][:cap]
    if not active:
        active = [0]

    active_set = frozenset(active)
    nbr: dict[int, set[int]] = defaultdict(set)
    by_area: dict[int, list[int]] = defaultdict(list)
    for f in active_set:
        by_area[f // FAMILIES_PER_AREA].append(f)
    for lst in by_area.values():
        lst.sort()
        for i, f in enumerate(lst):
            if i:
                nbr[f].add(lst[i - 1])
            if i + 1 < len(lst):
                nbr[f].add(lst[i + 1])

    hex_x = {str(k): float(v) for k, v in state.hex_x.items()}
    hex_p = {str(k): float(v) for k, v in state.hex_p.items()}
    for k in list(hex_x.keys()):
        if int(k) not in active_set:
            del hex_x[k]
            hex_p.pop(k, None)

    for f in active_set:
        fk = str(f)
        prev_x = float(hex_x.get(fk, 1.0 / NUM_FAMILIES))
        prev_p = float(hex_p.get(fk, 0.0))
        src = float(hitn[f])
        nb = nbr[f]
        if nb:
            navg = sum(float(hex_x.get(str(g), prev_x)) for g in nb) / len(nb)
        else:
            navg = prev_x
        area_a = f // FAMILIES_PER_AREA
        c_loc = float(sig[area_a]) if area_a < NUM_AREAS else 0.0
        na = max(1, sum(1 for x in active_set if x // FAMILIES_PER_AREA == area_a))
        x_new = (
            (1.0 - th.lambda_h) * prev_x
            + th.theta_c * src
            + th.theta_d * navg
            - th.theta_p * prev_p
        )
        x_new = float(np.clip(x_new, 0.0, 1.0))
        p_new = (1.0 - th.mu_h) * prev_p + th.delta_h * (c_loc / na) - th.rho_h
        p_new = max(0.0, p_new)
        hex_x[fk] = x_new
        hex_p[fk] = p_new

    return FieldDynamicsState(
        t=state.t,
        area_a=state.area_a.copy(),
        p_a=state.p_a.copy(),
        stab=state.stab,
        concept_mass=state.concept_mass,
        f_f=state.f_f.copy(),
        p_family=state.p_family.copy(),
        hex_x=hex_x,
        hex_p=hex_p,
        l8_cluster_mass_prev=dict(getattr(state, "l8_cluster_mass_prev", {}) or {}),
        version=4,
    )


def family_vector_from_hex(hex_x: dict[str, float]) -> np.ndarray:
    v = np.zeros(NUM_FAMILIES, dtype=np.float64)
    for f in range(NUM_FAMILIES):
        v[f] = float(hex_x.get(str(f), 0.0))
    s = float(v.sum())
    if s <= 0:
        return np.full(NUM_FAMILIES, 1.0 / NUM_FAMILIES)
    return v / s


def area_vector_from_hex(hex_x: dict[str, float]) -> np.ndarray:
    area = np.zeros(NUM_AREAS, dtype=np.float64)
    for f in range(NUM_FAMILIES):
        area[f // FAMILIES_PER_AREA] += float(hex_x.get(str(f), 0.0))
    s = float(area.sum())
    if s <= 0:
        return np.full(NUM_AREAS, 1.0 / NUM_AREAS)
    return area / s


def blend_hit_with_hex_family(hitn: list[float], hex_x: dict[str, float], w: float) -> list[float]:
    w = float(np.clip(w, 0.0, 1.0))
    h = np.asarray(hitn, dtype=np.float64).reshape(NUM_FAMILIES)
    h = h / h.sum() if h.sum() > 0 else np.full(NUM_FAMILIES, 1.0 / NUM_FAMILIES)
    x = family_vector_from_hex(hex_x)
    out = w * h + (1.0 - w) * x
    out = out / out.sum()
    return [float(out[i]) for i in range(NUM_FAMILIES)]


def blend_hit_with_hex_area(hit_area: list[float], hex_x: dict[str, float], w: float) -> list[float]:
    w = float(np.clip(w, 0.0, 1.0))
    a = np.asarray(hit_area, dtype=np.float64).reshape(NUM_AREAS)
    a = a / a.sum() if a.sum() > 0 else np.full(NUM_AREAS, 1.0 / NUM_AREAS)
    x = area_vector_from_hex(hex_x)
    out = w * a + (1.0 - w) * x
    out = out / out.sum()
    return [float(out[i]) for i in range(NUM_AREAS)]


def field_dynamics_phase3_enabled() -> bool:
    import os

    return os.environ.get("HESPERIA_FIELD_DYNAMICS_PHASE3", "").strip().lower() in ("1", "true", "yes")


def field_dynamics_hex_cap_from_env(default: int = 128) -> int:
    import os

    raw = os.environ.get("HESPERIA_FIELD_DYNAMICS_HEX_CAP", "").strip()
    if not raw:
        return default
    try:
        return max(8, min(int(raw), NUM_FAMILIES))
    except ValueError:
        return default
