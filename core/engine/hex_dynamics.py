# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Hex microphysical field dynamics (Option A: hex-primary; F = P_HF H derived).

Engine Dynamics v0.5: continuous Euler + §7b local discrete (``step_hex_local_microphysics``), with optional
**energy-controlled** stepping via ``core.engine.energy.EnergyControlParams`` (dt halving / line search).
Ring = minimal W_H; cross-family hex diffusion not modeled here (swampy for full lattice).
Spec: spec/hex_microphysics_canon.md
"""

from __future__ import annotations

import dataclasses
import warnings
from dataclasses import dataclass
from typing import Any, Iterator

import numpy as np

from core.engine.energy import (
    EnergyControlParams,
    EnergyMode,
    apply_clip_01_with_stats,
    compute_energy_hex_2d,
    energy_acceptable,
)
from core.engine.hex_matrix_builders import (
    HEXES_PER_FAMILY_CANON,
    NUM_FAMILIES_HEX,
    apply_pch_to_concept_activation,
    build_ring_laplacian,
    build_uniform_hex_resistance,
)

__all__ = [
    "HexFieldParams",
    "HexObservables",
    "LocalHexMicrophysicsParams",
    "family_aggregate_from_hex",
    "canonical_family_field",
    "hex_source_from_concept_family_injection",
    "run_option_a_hex_primary",
    "step_hex_field_euler",
    "step_hex_local_microphysics",
    "run_hex_microphysics",
    "RunHexMicrophysicsOutcome",
    "compute_hex_observables",
    "ring_cluster_compactness",
]


@dataclass(frozen=True)
class LocalHexMicrophysicsParams:
    """§7b discrete local update coefficients."""

    alpha: float = 0.08
    beta: float = 0.05
    gamma: float = 0.06


@dataclass(frozen=True)
class HexFieldParams:
    alpha_H: float = 0.12
    beta_H: float = 0.06
    gamma_H: float = 0.10
    delta_H: float = 0.22
    dt: float = 0.05
    clip_01: bool = True
    activation_threshold: float = 1e-6

    def validate(self) -> None:
        for name in ("alpha_H", "beta_H", "gamma_H", "delta_H", "dt"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be >= 0")
        if self.dt == 0:
            raise ValueError("dt must be > 0")


@dataclass(frozen=True)
class HexObservables:
    E_H: float
    K_H: float
    R_H_load: float
    G_H: float
    compactness: float
    G_F: float

    def as_dict(self) -> dict[str, float]:
        return {
            "E_H": self.E_H,
            "K_H": self.K_H,
            "R_H_load": self.R_H_load,
            "G_H": self.G_H,
            "hex_cluster_compactness": self.compactness,
            "family_grounding_G_F": self.G_F,
        }


@dataclass
class RunHexMicrophysicsOutcome:
    """``run_hex_microphysics`` return value; unpackable as ``(H, obs_series)``."""

    H: np.ndarray
    obs_series: list[HexObservables]
    energy_trace: list[float]
    convergence_flag: bool
    steps_to_convergence: int

    def __iter__(self) -> Iterator[Any]:
        yield self.H
        yield self.obs_series


def family_aggregate_from_hex(H: np.ndarray) -> np.ndarray:
    """F = P_HF H (sum over hex slots per family)."""
    arr = np.asarray(H, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError("H must be 2D (n_families, n_hex_per_family)")
    return arr.sum(axis=1)


def canonical_family_field(H: np.ndarray) -> np.ndarray:
    """
    Official mesoscopic family state under Option A: **F = P_HF H**.

    Same as ``family_aggregate_from_hex``; use this name when asserting
    structural closure (spec §9).
    """
    return family_aggregate_from_hex(H)


def hex_source_from_concept_family_injection(
    family_weights: np.ndarray | list[float],
    *,
    n_hex_per_family: int | None = None,
) -> np.ndarray:
    """
    **S_H** = first ``len(family_weights)`` family rows of reshape(**P_CH** @ **a_concept**).

    ``family_weights`` is padded/truncated to **N_concept** inside ``apply_pch_to_concept_activation``.
    Production **P_CH** is required (``core.engine.pch_loader.load_pch``); uniform spread is forbidden.
    """
    from core.engine.pch_loader import load_pch

    wf = np.maximum(0.0, np.asarray(family_weights, dtype=np.float64).reshape(-1))
    nf_user = int(wf.shape[0])
    nh = int(n_hex_per_family or HEXES_PER_FAMILY_CANON)
    pch = load_pch()
    full = apply_pch_to_concept_activation(
        wf, pch, n_families=NUM_FAMILIES_HEX, n_hex_per_family=nh
    )
    if nf_user > full.shape[0]:
        raise ValueError(
            f"family_weights length {nf_user} exceeds canonical families {full.shape[0]}"
        )
    return np.asarray(full[:nf_user, :], dtype=np.float64)


def run_option_a_hex_primary(
    family_injection: np.ndarray | list[float],
    C_F: np.ndarray,
    *,
    params: HexFieldParams | None = None,
    n_steps: int = 20,
    H0: np.ndarray | None = None,
    r_uniform: float = 0.5,
) -> dict[str, Any]:
    """
    Single entrypoint for Option A closure: concept evidence → hex source → evolve **H** → **F = P_HF H**.

    ``family_injection`` is **P_CF A** (length Nf). Hex source **S_H** is built via
    ``hex_source_from_concept_family_injection``. Returns **H**, canonical **F**,
    final observables (**G_F** = 1 by construction), and timeline observables.
    """
    p = params or HexFieldParams()
    wf = np.maximum(0.0, np.asarray(family_injection, dtype=np.float64).reshape(-1))
    nf = wf.shape[0]
    nh = HEXES_PER_FAMILY_CANON
    S_H = hex_source_from_concept_family_injection(wf, n_hex_per_family=nh)
    if S_H.shape != (nf, nh):
        raise ValueError("family_injection length defines n_families")
    C = np.asarray(C_F, dtype=np.float64)
    if C.shape != (nf, nf):
        raise ValueError(f"C_F must be ({nf},{nf})")
    L = build_ring_laplacian(nh)
    R = build_uniform_hex_resistance(nf, nh, r_uniform)
    if H0 is not None:
        H_init = np.asarray(H0, dtype=np.float64)
        if H_init.shape != (nf, nh):
            raise ValueError("H0 shape must be (n_families, n_hex_per_family)")
    else:
        H_init = np.zeros((nf, nh), dtype=np.float64)

    H, obs_series = run_hex_microphysics(
        H_init, S_H, L, R, C, p, n_steps=n_steps
    )
    F_canon = canonical_family_field(H)
    last_obs = compute_hex_observables(
        H, L, R, C, p.activation_threshold, F_external=F_canon
    )
    return {
        "H": H,
        "F_canonical": F_canon,
        "S_H": S_H,
        "hex_observables_final": last_obs,
        "hex_observables_timeline": obs_series,
        "params": p,
        "closure": "Option_A_F_equals_P_HF_H",
    }


def _apply_ring_laplacian(L: np.ndarray, H_row: np.ndarray) -> np.ndarray:
    return L @ H_row


def _step_hex_local_microphysics_raw(
    A: np.ndarray,
    R: np.ndarray,
    C_F: np.ndarray,
    params: LocalHexMicrophysicsParams,
) -> np.ndarray:
    """One local §7b update without clipping (for energy line search)."""
    nf, nh = A.shape
    S = A.sum(axis=1)
    cpress = C_F @ S
    A_new = np.zeros_like(A)
    for m in range(nf):
        for k in range(nh):
            an = A[m, (k - 1) % nh] + A[m, (k + 1) % nh]
            lap = an - 2.0 * A[m, k]
            dh = params.alpha * lap - params.beta * R[m, k] * A[m, k] - params.gamma * float(cpress[m])
            A_new[m, k] = A[m, k] + dh
    return A_new


def step_hex_local_microphysics(
    A: np.ndarray,
    R: np.ndarray,
    C_F: np.ndarray,
    *,
    params: LocalHexMicrophysicsParams | None = None,
    clip_nonneg: bool = True,
    S_H: np.ndarray | None = None,
    L_ring: np.ndarray | None = None,
    energy_control: EnergyControlParams | None = None,
    lam_contra: float = 1.0,
) -> np.ndarray:
    """
    A_h' = A_h + α Σ_{n∈N(h)}(A_n - A_h) - β R_h A_h - γ C_h.
    Ring neighborhood within each family row; C_h = (C_F @ S)_m for hexes in family m.

    With ``energy_control``, requires ``S_H`` and ``L_ring``; uses line search on the update
    so ``compute_energy_hex_2d`` does not increase (strict/soft per config).
    """
    p = params or LocalHexMicrophysicsParams()
    A = np.asarray(A, dtype=np.float64)
    R = np.asarray(R, dtype=np.float64)
    C = np.asarray(C_F, dtype=np.float64)
    if A.ndim != 2 or R.shape != A.shape:
        raise ValueError("A and R must be 2D and same shape")
    nf, nh = A.shape
    if C.shape != (nf, nf):
        raise ValueError("C_F must be (nf, nf)")

    A_raw = _step_hex_local_microphysics_raw(A, R, C, p)

    if energy_control is None:
        if clip_nonneg:
            return np.maximum(A_raw, 0.0)
        return A_raw

    if S_H is None or L_ring is None:
        raise ValueError("energy_control requires S_H and L_ring for hex energy bookkeeping")
    s_h = np.asarray(S_H, dtype=np.float64)
    l_ring = np.asarray(L_ring, dtype=np.float64)
    if s_h.shape != A.shape or l_ring.shape != (nh, nh):
        raise ValueError("S_H / L_ring shape mismatch for energy-controlled local step")

    E0 = compute_energy_hex_2d(A, l_ring, C, s_h, lam_contra=lam_contra)
    dA = A_raw - A
    mass_in = float(np.sum(A))
    # Soft energy control must not accept proposals that annihilate positive mass: η=1 with a
    # strongly negative raw update can clip to all zeros while lowering energy (degenerate for
    # diffuse priors e.g. uniform marker fallback when lexicon has no hits).
    min_mass_floor = max(1e-30, mass_in * 1e-18)
    for eta in energy_control.line_search_factors:
        At = A + eta * dA
        if clip_nonneg:
            At = np.maximum(At, 0.0)
        if mass_in > 1e-30 and float(np.sum(At)) < min_mass_floor:
            continue
        E1 = compute_energy_hex_2d(At, l_ring, C, s_h, lam_contra=lam_contra)
        if energy_acceptable(E0, E1, energy_control):
            return At
    if energy_control.mode == EnergyMode.strict:
        raise RuntimeError(
            "Energy-controlled hex local step: no line-search factor satisfied energy acceptance."
        )
    return np.maximum(A, 0.0) if clip_nonneg else A.copy()


def _propose_hex_euler_step(
    H: np.ndarray,
    S_H: np.ndarray,
    L_ring: np.ndarray,
    R_coeff: np.ndarray,
    C_F: np.ndarray,
    params: HexFieldParams,
    dt: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Euler proposal ``H + dt * dH`` (before optional clip)."""
    nf, nh = H.shape
    S_family = H.sum(axis=1)
    c_f_s = C_F @ S_family
    dH = np.zeros_like(H)
    for m in range(nf):
        lh = _apply_ring_laplacian(L_ring, H[m])
        dH[m] = (
            -params.alpha_H * lh
            -params.beta_H * R_coeff[m] * H[m]
            -params.gamma_H * H[m] * float(c_f_s[m])
            + params.delta_H * S_H[m]
        )
    H_next = H + dt * dH
    return H_next, dH


def step_hex_field_euler(
    H: np.ndarray,
    S_H: np.ndarray,
    L_ring: np.ndarray,
    R_coeff: np.ndarray,
    C_F: np.ndarray,
    params: HexFieldParams,
    *,
    energy_control: EnergyControlParams | None = None,
    lam_contra: float = 1.0,
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    One explicit Euler step on H (n_f × n_h).

    With ``energy_control``, reduces ``dt`` until ``compute_energy_hex_2d`` is non-increasing
    (strict/soft). Clipping to ``[0,1]`` is a safeguard; excessive clipping can raise.
    """
    params.validate()
    H = np.asarray(H, dtype=np.float64)
    S_H = np.asarray(S_H, dtype=np.float64)
    R_coeff = np.asarray(R_coeff, dtype=np.float64)
    C_F = np.asarray(C_F, dtype=np.float64)
    L_ring = np.asarray(L_ring, dtype=np.float64)
    if H.shape != S_H.shape:
        raise ValueError("H and S_H must have same shape")
    nf, nh = H.shape
    if L_ring.shape != (nh, nh):
        raise ValueError("L_ring shape mismatch")
    if R_coeff.shape != (nf, nh):
        raise ValueError("R_coeff shape must match H")
    if C_F.shape != (nf, nf):
        raise ValueError(f"C_F must be ({nf},{nf})")

    lam = float(lam_contra)

    def _energy(h: np.ndarray) -> float:
        return float(compute_energy_hex_2d(h, L_ring, C_F, S_H, lam_contra=lam))

    S_family = H.sum(axis=1)

    if energy_control is None:
        H_next, dH = _propose_hex_euler_step(
            H, S_H, L_ring, R_coeff, C_F, params, params.dt
        )
        clip_frac = 0.0
        if params.clip_01:
            H_next, clip_frac = apply_clip_01_with_stats(H_next, clip=True)
        e0, e1 = _energy(H), _energy(H_next)
        return H_next, {
            "delta_H_norm": float(np.linalg.norm(dH.ravel(), ord=2)),
            "family_mass": S_family.copy(),
            "dt_effective": float(params.dt),
            "n_dt_retries": 0,
            "clip_fraction": clip_frac,
            "energy_prev": e0,
            "energy_next": e1,
            "energy_descent_satisfied": True,
        }

    dt = float(params.dt)
    n_retries = 0
    E_prev = _energy(H)
    H_next = H.copy()
    dH = np.zeros_like(H)
    clip_frac = 0.0
    descent_ok = True

    while True:
        H_prop, dH = _propose_hex_euler_step(H, S_H, L_ring, R_coeff, C_F, params, dt)
        if params.clip_01:
            H_prop, clip_frac = apply_clip_01_with_stats(H_prop, clip=True)
        else:
            clip_frac = 0.0
        E_next = _energy(H_prop)
        if energy_acceptable(E_prev, E_next, energy_control):
            H_next = H_prop
            break
        n_retries += 1
        dt *= energy_control.dt_decay
        if dt < energy_control.dt_min or n_retries > energy_control.max_dt_halving_retries:
            if energy_control.mode == EnergyMode.strict:
                raise RuntimeError(
                    "Energy-controlled hex Euler step: could not achieve acceptable energy change "
                    f"after {n_retries} dt reductions (dt={dt})."
                )
            descent_ok = False
            H_next = H_prop
            break

    if clip_frac >= energy_control.clip_fail_threshold:
        raise RuntimeError(
            f"Excessive [0,1] clipping ({clip_frac:.3f}) on hex field step; reduce dt or params."
        )
    if clip_frac >= energy_control.clip_warn_threshold:
        warnings.warn(
            f"High clip fraction {clip_frac:.3f} on hex Euler step.",
            RuntimeWarning,
            stacklevel=2,
        )

    return H_next, {
        "delta_H_norm": float(np.linalg.norm(dH.ravel(), ord=2)),
        "family_mass": S_family.copy(),
        "dt_effective": float(dt),
        "n_dt_retries": n_retries,
        "clip_fraction": clip_frac,
        "energy_prev": E_prev,
        "energy_next": float(_energy(H_next)),
        "energy_descent_satisfied": descent_ok,
    }


def run_hex_microphysics(
    H0: np.ndarray,
    S_H: np.ndarray,
    L_ring: np.ndarray,
    R_coeff: np.ndarray,
    C_F: np.ndarray,
    params: HexFieldParams,
    *,
    n_steps: int,
    energy_control: EnergyControlParams | None = None,
    lam_contra: float | None = None,
) -> RunHexMicrophysicsOutcome:
    H = np.asarray(H0, dtype=np.float64).copy()
    obs_series: list[HexObservables] = []
    lam = (
        float(lam_contra)
        if lam_contra is not None
        else float(max(params.gamma_H, 1e-12) / max(params.alpha_H, 1e-12))
    )
    energy_trace: list[float] = []
    if energy_control is not None:
        energy_trace.append(
            float(compute_energy_hex_2d(H, L_ring, C_F, S_H, lam_contra=lam))
        )

    current_dt = float(params.dt)
    stable = 0
    converged = False
    steps_done = n_steps

    for i in range(n_steps):
        H_prev = H.copy()
        p_step = dataclasses.replace(params, dt=current_dt)
        H, diag = step_hex_field_euler(
            H,
            S_H,
            L_ring,
            R_coeff,
            C_F,
            p_step,
            energy_control=energy_control,
            lam_contra=lam,
        )
        obs_series.append(
            compute_hex_observables(H, L_ring, R_coeff, C_F, params.activation_threshold)
        )
        if energy_control is not None:
            energy_trace.append(
                float(compute_energy_hex_2d(H, L_ring, C_F, S_H, lam_contra=lam))
            )
            if diag.get("energy_descent_satisfied") and energy_acceptable(
                float(diag["energy_prev"]),
                float(diag["energy_next"]),
                energy_control,
            ):
                stable += 1
            else:
                stable = 0
            current_dt = float(diag.get("dt_effective", current_dt))
            if stable >= energy_control.stable_steps_for_growth:
                current_dt = min(current_dt * energy_control.dt_growth, energy_control.dt_max)
                stable = 0
            delta_a = float(np.linalg.norm(H.ravel() - H_prev.ravel(), ord=2))
            delta_e = abs(float(diag["energy_next"]) - float(diag["energy_prev"]))
            if (
                delta_a < energy_control.epsilon_delta_a
                and delta_e < energy_control.epsilon_delta_e
            ):
                converged = True
                steps_done = i + 1
                break

    return RunHexMicrophysicsOutcome(
        H=H,
        obs_series=obs_series,
        energy_trace=energy_trace,
        convergence_flag=converged,
        steps_to_convergence=steps_done,
    )


def ring_cluster_compactness(h_row: np.ndarray, theta: float) -> float:
    """
    Comp = (Σ |C_i|²) / (Σ |C_i|)² for active hexes on a ring (binary activation h > theta).
    """
    h_row = np.asarray(h_row, dtype=np.float64).reshape(-1)
    n = h_row.shape[0]
    act = [i for i in range(n) if h_row[i] > theta]
    t = len(act)
    if t == 0:
        return 1.0
    act_set = set(act)
    seen: set[int] = set()
    comps: list[int] = []
    for i in act:
        if i in seen:
            continue
        sz = 0
        stack = [i]
        while stack:
            u = stack.pop()
            if u in seen or u not in act_set:
                continue
            seen.add(u)
            sz += 1
            for v in ((u - 1) % n, (u + 1) % n):
                if v in act_set and v not in seen:
                    stack.append(v)
        comps.append(sz)
    num = sum(c * c for c in comps)
    den = t * t
    return float(num / den) if den > 0 else 1.0


def global_hex_compactness(H: np.ndarray, theta: float) -> float:
    """Mass-weighted mean of per-family ring compactness."""
    H = np.asarray(H, dtype=np.float64)
    masses = H.sum(axis=1)
    w = masses.sum()
    if w <= 0:
        return 1.0
    acc = 0.0
    for m in range(H.shape[0]):
        c = ring_cluster_compactness(H[m], theta)
        acc += masses[m] * c
    return float(acc / w)


def compute_hex_observables(
    H: np.ndarray,
    L_ring: np.ndarray,
    R_coeff: np.ndarray,
    C_F: np.ndarray,
    activation_threshold: float,
    *,
    F_external: np.ndarray | None = None,
    eps: float = 1e-9,
) -> HexObservables:
    """§10 observables; K_H = S^T C_F S."""
    H = np.asarray(H, dtype=np.float64)
    nf, nh = H.shape
    e_h = 0.0
    g_h_sq = 0.0
    r_load = 0.0
    for m in range(nf):
        hm = H[m]
        lh = L_ring @ hm
        e_h += 0.5 * float(hm @ lh)
        g_h_sq += float(lh @ lh)
        r_load += float(np.sum(hm * R_coeff[m] * hm))
    s = H.sum(axis=1)
    k_h = float(s @ (C_F @ s))
    comp = global_hex_compactness(H, activation_threshold)
    f_agg = s
    if F_external is None:
        g_f = 1.0
    else:
        fe = np.asarray(F_external, dtype=np.float64).reshape(-1)
        if fe.shape[0] != nf:
            raise ValueError("F_external length must match n_families")
        num = float(np.linalg.norm(fe - f_agg, ord=2))
        den = float(np.linalg.norm(fe, ord=2)) + eps
        g_f = float(np.clip(1.0 - num / den, 0.0, 1.0))
    return HexObservables(
        E_H=e_h,
        K_H=k_h,
        R_H_load=r_load,
        G_H=float(np.sqrt(g_h_sq)),
        compactness=comp,
        G_F=g_f,
    )
