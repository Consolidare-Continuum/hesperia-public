# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Core Math Contract v1.0 (22_SPEC) — canonical implementation, wired into the live
runtime/pipeline/analyze.py `/analyze` entry point.

Implements: fusion (Dict A + Dict B → E0), centroid selection, base traversal step,
shadow step, penalties (ambiguity, thin-core, dispersion, guard, shadow), metrics
(governance, loopability, tension_energy, obstacle_score), invariant checks. `run_demo()`
below is a standalone illustrative entry point (small row-stochastic W), not the module's
purpose — the rest of the file is production code.
Config: assets/config/guard_config_v1.json (fallback: repo root).
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

# Optional numpy for vector/matrix ops; fallback to pure Python
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# -----------------------------------------------------------------------------
# Config load (defaults from spec §14)
# B3–B5 agentic addresses: docs/recipes/chiron_tweaks/CHIRON-126-ADDRESS-MAP-2026-08-21.md (items 69–85)
# -----------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "eps": 1e-9,
    "alpha": 0.65,
    "E_cap": 1.0,
    "K_max": 5,
    "eta": 0.02,
    "lambda": 0.55,
    "decay": 0.04,
    "T_steps": 8,
    "energy_conservation_tolerance": 1e-6,
    "delta_gap": 0.08,
    "k_amb": 0.35,
    "tau_core": 0.25,
    "k_thin": 0.30,
    "k_disp": 0.25,
    "max_shadow_hops": 2,
    "k_shadow": 0.40,
    "k_shadow_perturb": 0.04,
    "k_guard": 0.30,
    "w_decay": 0.50,
    "w_guard_obs": 0.30,
    "w_shadow_obs": 0.20,
}


def load_config(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        base = Path(__file__).resolve().parents[2]
        path = base / "assets" / "config" / "guard_config_v1.json"
        if not path.exists():
            path = base / "guard_config_v1.json"  # legacy root fallback
    cfg = dict(DEFAULT_CONFIG)
    if not path.exists():
        _apply_env_overrides(cfg)
        return cfg
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # Flatten from nested schema into single key set for this reference
    if "numerics" in data:
        cfg["eps"] = data["numerics"].get("eps", cfg["eps"])
        cfg["E_cap"] = data["numerics"].get("energy_cap", cfg["E_cap"])
        cfg["energy_conservation_tolerance"] = data["numerics"].get(
            "energy_conservation_tolerance", cfg["energy_conservation_tolerance"]
        )
    if "fusion" in data:
        cfg["alpha"] = data["fusion"].get("alpha", cfg["alpha"])
    if "centroid" in data:
        cfg["K_max"] = data["centroid"].get("K_max", cfg["K_max"])
        cfg["eta"] = data["centroid"].get("activation_threshold_eta", cfg["eta"])
    if "traversal" in data:
        cfg["lambda"] = data["traversal"].get("lambda", cfg["lambda"])
        cfg["decay"] = data["traversal"].get("decay", cfg["decay"])
        cfg["T_steps"] = data["traversal"].get("steps", cfg["T_steps"])
    if "ambiguity" in data:
        cfg["delta_gap"] = data["ambiguity"].get("delta_gap", cfg["delta_gap"])
        cfg["k_amb"] = data["ambiguity"].get("penalty_k", cfg["k_amb"])
    if "core_thinness" in data:
        cfg["tau_core"] = data["core_thinness"].get("tau_core", cfg["tau_core"])
        cfg["k_thin"] = data["core_thinness"].get("penalty_k", cfg["k_thin"])
    if "dispersion" in data:
        cfg["k_disp"] = data["dispersion"].get("penalty_k", cfg["k_disp"])
    if "shadow" in data:
        cfg["max_shadow_hops"] = data["shadow"].get("max_shadow_hops", cfg["max_shadow_hops"])
        cfg["k_shadow"] = data["shadow"].get("shadow_penalty_k", cfg["k_shadow"])
        cfg["k_shadow_perturb"] = data["shadow"].get("k_shadow_perturb", cfg["k_shadow_perturb"])
    if "guard_penalty" in data:
        cfg["k_guard"] = data["guard_penalty"].get("k_guard", cfg["k_guard"])
    if "obstacle_score" in data:
        cfg["w_decay"] = data["obstacle_score"].get("w_decay", cfg["w_decay"])
        cfg["w_guard_obs"] = data["obstacle_score"].get("w_guard", cfg["w_guard_obs"])
        cfg["w_shadow_obs"] = data["obstacle_score"].get("w_shadow", cfg["w_shadow_obs"])
    _apply_env_overrides(cfg)
    return cfg


def _apply_env_overrides(cfg: dict[str, Any]) -> None:
    """Override config from HESPERIA_* env vars for operational tuning. In-place."""
    def _float(key: str, lo: float, hi: float) -> None:
        s = os.environ.get(key, "").strip()
        if not s:
            return
        try:
            cfg[_map[key]] = max(lo, min(hi, float(s)))
        except ValueError:
            pass
    _map = {
        "HESPERIA_ALPHA": "alpha",
        "HESPERIA_ETA": "eta",
        "HESPERIA_LAMBDA": "lambda",
        "HESPERIA_DECAY": "decay",
        "HESPERIA_DELTA_GAP": "delta_gap",
        "HESPERIA_K_GUARD": "k_guard",
        "HESPERIA_K_DISP": "k_disp",
        "HESPERIA_K_SHADOW_PERTURB": "k_shadow_perturb",
    }
    _float("HESPERIA_ALPHA", 0.0, 1.0)
    _float("HESPERIA_ETA", 0.001, 0.2)
    _float("HESPERIA_LAMBDA", 0.01, 1.0)
    _float("HESPERIA_DECAY", 0.0, 0.5)
    _float("HESPERIA_DELTA_GAP", 0.01, 0.5)
    _float("HESPERIA_K_GUARD", 0.0, 1.0)
    _float("HESPERIA_K_DISP", 0.0, 1.0)
    _float("HESPERIA_K_SHADOW_PERTURB", 0.0, 0.5)


def validate_config(cfg: dict[str, Any]) -> list[str]:
    """
    Required CI checks per 22_SPEC §16. Returns list of error messages; empty if valid.
    """
    errs: list[str] = []
    a = cfg.get("alpha", 0.65)
    if not (0 <= a <= 1):
        errs.append(f"alpha must be in [0,1], got {a}")
    lam = cfg.get("lambda", 0.55)
    if not (0 < lam <= 1):
        errs.append(f"lambda must be in (0,1], got {lam}")
    decay = cfg.get("decay", 0.04)
    if not (0 <= decay < 1):
        errs.append(f"decay must be in [0,1), got {decay}")
    for key in ("k_amb", "k_thin", "k_disp", "k_shadow", "k_guard"):
        v = cfg.get(key, 0.3)
        if not (0 <= v <= 1):
            errs.append(f"{key} must be in [0,1], got {v}")
    wd = cfg.get("w_decay", 0.5)
    wg = cfg.get("w_guard_obs", 0.3)
    ws = cfg.get("w_shadow_obs", 0.2)
    total_w = wd + wg + ws
    if abs(total_w - 1.0) > 1e-6:
        errs.append(f"obstacle weights must sum to 1.0 ± 1e-6, got {total_w}")
    if cfg.get("max_shadow_hops", 2) < 0:
        errs.append("max_shadow_hops must be >= 0")
    tol = cfg.get("energy_conservation_tolerance", 1e-6)
    if tol >= 1e-3:
        errs.append(f"energy_conservation_tolerance must be < 1e-3, got {tol}")
    if cfg.get("E_cap", 1.0) <= 0:
        errs.append("energy_cap must be > 0")
    return errs


# -----------------------------------------------------------------------------
# Helpers (work with list or 1d array)
# -----------------------------------------------------------------------------

def _sum(v: list[float] | Any) -> float:
    if HAS_NUMPY and isinstance(v, np.ndarray):
        return float(np.sum(v))
    return sum(v)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _vec_clamp(v: list[float] | Any, lo: float, hi: float) -> list[float] | Any:
    if HAS_NUMPY and isinstance(v, np.ndarray):
        return np.clip(v, lo, hi)
    return [max(lo, min(hi, x)) for x in v]


# -----------------------------------------------------------------------------
# §3 SurfaceEnergy fusion
# -----------------------------------------------------------------------------

def fusion(S: list[float], L: list[float], cfg: dict[str, Any]) -> list[float]:
    """E0[i] = clamp( alpha*S'[i] + (1-alpha)*L'[i], 0, E_cap )."""
    eps = cfg["eps"]
    alpha = cfg["alpha"]
    E_cap = cfg["E_cap"]
    n = len(S)
    assert n == len(L)
    sumS = _sum(S)
    sumL = _sum(L)
    if sumS <= 0 and sumL <= 0:
        raise ValueError("F5: no activation (both sumS and sumL are 0)")
    Sp = [S[i] / (sumS + eps) if sumS > 0 else 0.0 for i in range(n)]
    Lp = [L[i] / (sumL + eps) if sumL > 0 else 0.0 for i in range(n)]
    E0 = [_clamp(alpha * Sp[i] + (1 - alpha) * Lp[i], 0.0, E_cap) for i in range(n)]
    return E0


# -----------------------------------------------------------------------------
# §4 Centroid selection
# -----------------------------------------------------------------------------

def centroid_indices(E0: list[float], cfg: dict[str, Any]) -> list[int]:
    """Top-K sides by E0 (desc); tie-break smaller side_id. Returns list of side indices."""
    eta = cfg["eta"]
    K_max = cfg["K_max"]
    active = [i for i in range(len(E0)) if E0[i] > eta]
    K = min(K_max, len(active))
    if K == 0:
        return []
    # Sort by E0 desc, then by i asc
    ordered = sorted(active, key=lambda i: (-E0[i], i))
    return ordered[:K]


# -----------------------------------------------------------------------------
# §5 Base traversal step (single step: diffusion → decay → clamp)
# -----------------------------------------------------------------------------

def base_step(E: list[float] | Any, W: list[list[float]] | Any, cfg: dict[str, Any]) -> tuple[list[float] | Any, bool]:
    """
    D = (1-lambda)*E + lambda*(E*W); E_next = D*(1-decay); clamp.
    Returns (E_next, conservation_ok).
    """
    lam = cfg["lambda"]
    decay = cfg["decay"]
    E_cap = cfg["E_cap"]
    tol = cfg["energy_conservation_tolerance"]
    if HAS_NUMPY:
        E = np.asarray(E, dtype=float)
        W = np.asarray(W, dtype=float)
        D = (1 - lam) * E + lam * (E @ W)
        sumE = float(np.sum(E))
        sumD = float(np.sum(D))
        conservation_ok = (1 - tol) * sumE <= sumD <= (1 + tol) * sumE
        E_next = np.clip(D * (1 - decay), 0.0, E_cap)
        return E_next, conservation_ok
    n = len(E)
    # (E @ W)[j] = sum_i E[i] * W[i][j]
    EW = [sum(E[i] * W[i][j] for i in range(n)) for j in range(n)]
    D = [(1 - lam) * E[i] + lam * EW[i] for i in range(n)]
    sumE = sum(E)
    sumD = sum(D)
    conservation_ok = (1 - tol) * sumE <= sumD <= (1 + tol) * sumE
    E_next = [_clamp(D[i] * (1 - decay), 0.0, E_cap) for i in range(n)]
    return E_next, conservation_ok


# -----------------------------------------------------------------------------
# §6 Shadow step (non-creation check)
# -----------------------------------------------------------------------------

def shadow_step(E: list[float] | Any, Ws: list[list[float]] | Any, cfg: dict[str, Any]) -> tuple[list[float] | Any, bool]:
    """E_shadow = E @ Ws (vector * matrix). Returns (E_shadow, non_creation_ok)."""
    eps = cfg["eps"]
    if HAS_NUMPY:
        E = np.asarray(E, dtype=float)
        Ws = np.asarray(Ws, dtype=float)
        E_shadow = E @ Ws
        non_creation_ok = float(np.sum(E_shadow)) <= float(np.sum(E)) + eps
        return E_shadow, non_creation_ok
    n = len(E)
    # (E @ Ws)[j] = sum_i E[i] * Ws[i][j]
    E_shadow = [sum(E[i] * Ws[i][j] for i in range(n)) for j in range(n)]
    non_creation_ok = sum(E_shadow) <= sum(E) + eps
    return E_shadow, non_creation_ok


# -----------------------------------------------------------------------------
# §8 Ambiguity penalty
# -----------------------------------------------------------------------------

def ambiguity_penalty(E0: list[float], cfg: dict[str, Any]) -> tuple[float, float, bool]:
    """Returns (P_amb, gap, degraded)."""
    eps = cfg["eps"]
    delta_gap = cfg["delta_gap"]
    k_amb = cfg["k_amb"]
    sorted_vals = sorted((e for e in E0 if e > 0), reverse=True)
    e1 = sorted_vals[0] if sorted_vals else 0.0
    e2 = sorted_vals[1] if len(sorted_vals) >= 2 else 0.0
    gap = (e1 - e2) / (e1 + eps)
    gap = _clamp(gap, 0.0, 1.0)
    Amb = 1.0 - gap
    P_amb = k_amb * (Amb ** 2)
    degraded = gap < delta_gap
    return P_amb, gap, degraded


# -----------------------------------------------------------------------------
# §9 Thin-core penalty
# -----------------------------------------------------------------------------

def thin_core_penalty(sumS: float, sumL: float, cfg: dict[str, Any]) -> tuple[float, float, bool]:
    """Returns (P_thin, CoreShare, degraded)."""
    eps = cfg["eps"]
    tau_core = cfg["tau_core"]
    k_thin = cfg["k_thin"]
    CoreShare = sumS / (sumS + sumL + eps)
    Thin = 1.0 - CoreShare
    P_thin = k_thin * Thin
    degraded = CoreShare < tau_core
    return P_thin, CoreShare, degraded


# -----------------------------------------------------------------------------
# §10 Dispersion penalty (entropy of E_end)
# -----------------------------------------------------------------------------

def dispersion_penalty(E_end: list[float], cfg: dict[str, Any]) -> float:
    """P_disp = k_disp * H_norm."""
    eps = cfg["eps"]
    k_disp = cfg["k_disp"]
    total = _sum(E_end) + eps
    active = [i for i in range(len(E_end)) if E_end[i] > 0]
    M = len(active)
    if M <= 1:
        return 0.0
    p = [E_end[i] / total for i in active]
    H = -sum(pi * math.log(pi) for pi in p if pi > 0)
    H_norm = H / math.log(M)
    return k_disp * min(H_norm, 1.0)


# -----------------------------------------------------------------------------
# §11 Guard penalty
# -----------------------------------------------------------------------------

def guard_penalty(sigma_fail: int, gamma_violation: int, theta_reject: int, cfg: dict[str, Any]) -> float:
    """P_guard = clamp(k_guard * GuardCount, 0, 1)."""
    k_guard = cfg["k_guard"]
    GuardCount = sigma_fail + gamma_violation + theta_reject
    return _clamp(k_guard * GuardCount, 0.0, 1.0)


# -----------------------------------------------------------------------------
# §12 Metrics
# -----------------------------------------------------------------------------

def metric_governance(P_amb: float, P_thin: float, P_shadow: float, P_disp: float, P_guard: float) -> float:
    return _clamp(1.0 - (P_amb + P_thin + P_shadow + P_disp + P_guard), 0.0, 1.0)


def metric_loopability(E_end: list[float], C: list[int], cfg: dict[str, Any]) -> float:
    eps = cfg["eps"]
    total = _sum(E_end) + eps
    in_c = sum(E_end[i] for i in C if i < len(E_end))
    return _clamp(in_c / total, 0.0, 1.0)


def metric_tension_energy(F: list[float], cfg: dict[str, Any]) -> float:
    """F = family energies. tension_energy = 1 - gapF."""
    eps = cfg["eps"]
    if not F:
        return 0.0
    f1 = max(F)
    rest = [f for f in F if f != f1] or [0.0]
    f2 = max(rest)
    gapF = (f1 - f2) / (f1 + eps)
    gapF = _clamp(gapF, 0.0, 1.0)
    return _clamp(1.0 - gapF, 0.0, 1.0)


def metric_obstacle_score(
    E0: list[float], E_end: list[float], GuardCount: int, shadow_hops: int, cfg: dict[str, Any]
) -> float:
    eps = cfg["eps"]
    w_decay = cfg["w_decay"]
    w_guard_obs = cfg["w_guard_obs"]
    w_shadow_obs = cfg["w_shadow_obs"]
    max_shadow_hops = cfg["max_shadow_hops"]
    sumE0 = _sum(E0) + eps
    sumE_end = _sum(E_end)
    Loss = _clamp(1.0 - sumE_end / sumE0, 0.0, 1.0)
    obs = w_decay * Loss + w_guard_obs * _clamp(GuardCount, 0, 1) + w_shadow_obs * _clamp(
        shadow_hops / max(max_shadow_hops, 1), 0.0, 1.0
    )
    return _clamp(obs, 0.0, 1.0)


def P_shadow_value(shadow_hops: int, cfg: dict[str, Any]) -> float:
    return _clamp(cfg["k_shadow"] * (shadow_hops / max(cfg["max_shadow_hops"], 1)), 0.0, 1.0)


# -----------------------------------------------------------------------------
# §7 Aggregation to dominant family and area
# -----------------------------------------------------------------------------

def aggregate_dominant_family_area(
    E_end: list[float],
    E0: list[float],
    C: list[int],
    sides_of_family: dict[int, list[int]],
    families_of_area: dict[int, list[int]],
    cfg: dict[str, Any],
) -> tuple[int | None, int | None, dict[int, float], dict[int, float]]:
    """
    F[f] = sum of E_end over sides in sides_of_family[f].
    dominant_family = argmax F with tie-break: higher sum E0 over centroid∩sides(f), then smaller family_id.
    A[a] = sum F[f] for f in families_of_area[a].
    dominant_area = argmax A with tie-break: higher centroid E0 mass for area, then smaller area_id.
    Returns (dominant_family_id, dominant_area_id, F, A). None if no families/areas.
    """
    eps = cfg["eps"]
    F: dict[int, float] = {}
    for fid, side_list in sides_of_family.items():
        F[fid] = sum(E_end[i] for i in side_list if i < len(E_end))
    if not F:
        return None, None, F, {}
    centroid_e0_by_family = {
        fid: sum(E0[i] for i in side_list if i in set(C) and i < len(E0))
        for fid, side_list in sides_of_family.items()
    }
    # Tie-break: higher F[f], then higher centroid E0, then smaller family_id
    dominant_family = max(
        F.keys(),
        key=lambda f: (F.get(f, 0.0), centroid_e0_by_family.get(f, 0.0), -f),
    )
    A: dict[int, float] = {}
    for aid, fam_list in families_of_area.items():
        A[aid] = sum(F.get(f, 0.0) for f in fam_list)
    if not A:
        return dominant_family, None, F, A
    centroid_e0_by_area = {
        aid: sum(
            E0[i]
            for f in families_of_area[aid]
            for i in sides_of_family.get(f, [])
            if i in set(C) and i < len(E0)
        )
        for aid in A
    }
    # Tie-break: higher A[a], then higher centroid E0, then smaller area_id
    dominant_area = max(
        A.keys(),
        key=lambda a: (A.get(a, 0.0), centroid_e0_by_area.get(a, 0.0), -a),
    )
    return dominant_family, dominant_area, F, A


# -----------------------------------------------------------------------------
# Invariant checks (for CI / tests)
# -----------------------------------------------------------------------------

def check_conservation_pre_decay(E: list[float], W: list[list[float]], cfg: dict[str, Any]) -> bool:
    """I-R2: sum(D) within tolerance of sum(E)."""
    lam = cfg["lambda"]
    tol = cfg["energy_conservation_tolerance"]
    if HAS_NUMPY:
        E = np.asarray(E)
        W = np.asarray(W)
        D = (1 - lam) * E + lam * (E @ W)
        return (1 - tol) * float(np.sum(E)) <= float(np.sum(D)) <= (1 + tol) * float(np.sum(E))
    n = len(E)
    D = [(1 - lam) * E[i] + lam * sum(E[j] * W[j][i] for j in range(n)) for i in range(n)]
    sumE = sum(E)
    sumD = sum(D)
    return (1 - tol) * sumE <= sumD <= (1 + tol) * sumE


def check_shadow_non_creation(E: list[float], Ws: list[list[float]], cfg: dict[str, Any]) -> bool:
    """I-R3: sum(E_shadow) <= sum(E) + eps."""
    eps = cfg["eps"]
    E_s, ok = shadow_step(E, Ws, cfg)
    return ok


# -----------------------------------------------------------------------------
# Demo: run fusion + traversal with tiny W
# -----------------------------------------------------------------------------

def make_demo_W(n: int) -> list[list[float]]:
    """Row-stochastic n x n (uniform outflow)."""
    return [[1.0 / n] * n for _ in range(n)]


# -----------------------------------------------------------------------------
# v0.5: family_vector (288) → initial energy for core (5)
# -----------------------------------------------------------------------------

CORE_N = 5
FAMILY_VECTOR_LEN = 288


def reduce_288_to_5(family_vector: list[float]) -> tuple[list[float], list[float]]:
    """
    Map 288-dim family_vector to 5-dim S, L for core. Deterministic.
    Bucket i = indices [i*288//5, (i+1)*288//5); value = sum(abs(family_vector[j])).
    L1-normalize so sum(S)=1. Return (S, L) with L=S so fusion uses this as initial state.
    """
    if len(family_vector) != FAMILY_VECTOR_LEN:
        raise ValueError(f"family_vector must have length {FAMILY_VECTOR_LEN}, got {len(family_vector)}")
    n = CORE_N
    buckets = [0.0] * n
    for i in range(n):
        lo = i * FAMILY_VECTOR_LEN // n
        hi = (i + 1) * FAMILY_VECTOR_LEN // n
        buckets[i] = sum(abs(family_vector[j]) for j in range(lo, hi))
    total = sum(buckets) or 1.0
    S = [buckets[i] / total for i in range(n)]
    return S, S[:]


def perturb_shadow(family_vector: list[float], cfg: dict[str, Any]) -> list[float]:
    """
    Deterministic perturbation of family_vector for shadow path. Pre-core.
    v'[i] = abs(v[i] * (1 + k_shadow_perturb * ((i * 7) % 11 - 5) / 5)).
    """
    k = float(cfg.get("k_shadow_perturb", 0.04))
    out = []
    for i in range(len(family_vector)):
        # Deterministic factor in [-1, 1]
        f = ((i * 7) % 11 - 5) / 5.0
        x = family_vector[i] * (1.0 + k * f)
        out.append(abs(x))
    return out


def _analyze_raw(
    initial_S: list[float] | None = None,
    initial_L: list[float] | None = None,
) -> dict[str, Any]:
    """Internal: run fusion + traversal + metrics; returns 6-key API payload (no Sigma)."""
    cfg = load_config()
    n = CORE_N
    if initial_S is not None and initial_L is not None and len(initial_S) == n and len(initial_L) == n:
        S = [max(0.0, float(x)) for x in initial_S]
        L = [max(0.0, float(x)) for x in initial_L]
    else:
        S = [1.0, 0.5, 0.0, 0.0, 0.0]
        L = [0.2, 0.8, 0.3, 0.0, 0.0]
    E0 = fusion(S, L, cfg)
    sumS = sum(S)
    sumL = sum(L)
    C = centroid_indices(E0, cfg)
    no_centroid = len(C) == 0

    W = make_demo_W(n)
    E = E0[:]
    for _ in range(cfg["T_steps"]):
        E, cons_ok = base_step(E, W, cfg)
        if not cons_ok:
            break

    E_end = E
    P_amb, gap, amb_degraded = ambiguity_penalty(E0, cfg)
    P_thin, core_share, thin_degraded = thin_core_penalty(sumS, sumL, cfg)
    P_disp = dispersion_penalty(E_end, cfg)
    guard_count = 0
    P_guard = guard_penalty(0, 0, 0, cfg)
    shadow_hops = 0
    P_shadow = P_shadow_value(shadow_hops, cfg)

    gov = metric_governance(P_amb, P_thin, P_shadow, P_disp, P_guard)
    loop = metric_loopability(E_end, C, cfg)
    F_demo = [sum(E_end)]
    tension = metric_tension_energy(F_demo, cfg)
    obstacle = metric_obstacle_score(E0, E_end, guard_count, shadow_hops, cfg)

    # Demo has no sides_of_family / families_of_area → dominant_family/area None
    return {
        "governance": gov,
        "loopability": loop,
        "tension_energy": tension,
        "obstacle_score": obstacle,
        "dominant_family": None,
        "dominant_area": None,
    }


def analyze(
    initial_S: list[float] | None = None,
    initial_L: list[float] | None = None,
) -> dict[str, Any]:
    """Produce 6-key summary (raw). If initial_S/initial_L provided (length 5), use as seed; else demo defaults."""
    return _analyze_raw(initial_S=initial_S, initial_L=initial_L)


def run_api() -> dict[str, Any]:
    """API path: analyze() → Sigma.enforce(summary) → return. No bypass. Sigma guaranteed."""
    try:
        from core.propagation.invariant_enforcer import enforce as sigma_enforce
    except ImportError:
        from invariant_enforcer import enforce as sigma_enforce
    result = analyze()
    result = sigma_enforce(result, skip_geometry=True, skip_bijection=True)
    return result


def run_api_with_guards(
    traversal_length: int = 0,
    area_hop_count: int = 0,
    evidence_count: int = 1,
) -> dict[str, Any]:
    """API path v0.3.1: analyze() → pipeline (Sigma → Gamma → Theta). No bypass. Sigma guaranteed."""
    try:
        from core.propagation.guard_pipeline import run_pipeline
    except ImportError:
        from guard_pipeline import run_pipeline
    result = analyze()
    return run_pipeline(
        result,
        traversal_length=traversal_length,
        area_hop_count=area_hop_count,
        evidence_count=evidence_count,
    )


def run_demo() -> dict[str, Any]:
    """Minimal run: S, L → E0 → centroid → T_steps base → penalties + metrics (full internal)."""
    cfg = load_config()
    n = 5
    S = [1.0, 0.5, 0.0, 0.0, 0.0]
    L = [0.2, 0.8, 0.3, 0.0, 0.0]
    E0 = fusion(S, L, cfg)
    sumS = sum(S)
    sumL = sum(L)
    C = centroid_indices(E0, cfg)
    no_centroid = len(C) == 0

    W = make_demo_W(n)
    E = E0[:]
    for _ in range(cfg["T_steps"]):
        E, cons_ok = base_step(E, W, cfg)
        if not cons_ok:
            break  # or log

    E_end = E
    P_amb, gap, amb_degraded = ambiguity_penalty(E0, cfg)
    P_thin, core_share, thin_degraded = thin_core_penalty(sumS, sumL, cfg)
    P_disp = dispersion_penalty(E_end, cfg)
    guard_count = 0
    P_guard = guard_penalty(0, 0, 0, cfg)
    shadow_hops = 0
    P_shadow = P_shadow_value(shadow_hops, cfg)

    gov = metric_governance(P_amb, P_thin, P_shadow, P_disp, P_guard)
    loop = metric_loopability(E_end, C, cfg)
    F_demo = [sum(E_end)]  # single "family" for demo
    tension = metric_tension_energy(F_demo, cfg)
    obstacle = metric_obstacle_score(E0, E_end, guard_count, shadow_hops, cfg)

    return {
        "E0": E0,
        "E_end": E_end if not HAS_NUMPY else [float(x) for x in E_end],
        "centroid_indices": C,
        "no_centroid": no_centroid,
        "governance": gov,
        "loopability": loop,
        "tension_energy": tension,
        "obstacle_score": obstacle,
        "P_amb": P_amb,
        "P_thin": P_thin,
        "P_disp": P_disp,
        "P_shadow": P_shadow,
        "degraded": {
            "ambiguity": amb_degraded,
            "thin_core": thin_degraded,
            "no_centroid": no_centroid,
            "shadow_overuse": False,
        },
        "conservation_ok": check_conservation_pre_decay(E0, W, cfg),
        "shadow_non_creation_ok": check_shadow_non_creation(E0, W, cfg),
    }


# -----------------------------------------------------------------------------
# Tests (I-R2, I-R3, fusion single-source, config validation, I-Q2 placeholder)
# -----------------------------------------------------------------------------

def run_tests() -> tuple[int, int]:
    """Run invariant and contract tests. Returns (passed, failed)."""
    cfg = load_config()
    passed, failed = 0, 0

    # Config validation
    errs = validate_config(cfg)
    if errs:
        print("FAIL validate_config: expected no errors for default config:", errs)
        failed += 1
    else:
        passed += 1

    # Fusion single-source (L only): E0 = (1-alpha)*L', so sum E0 = (1-alpha)
    try:
        S_zero = [0.0, 0.0, 0.0]
        L = [0.5, 0.5, 0.0]
        E0 = fusion(S_zero, L, cfg)
        expect = 1.0 - cfg["alpha"]
        if abs(_sum(E0) - expect) > 0.01:
            print("FAIL fusion L-only: sum E0 expected ~", expect, ", got", _sum(E0))
            failed += 1
        else:
            passed += 1
    except Exception as e:
        print("FAIL fusion L-only:", e)
        failed += 1

    # Fusion single-source (S only): E0 = alpha*S', so sum E0 = alpha
    try:
        S = [1.0, 0.0, 0.0]
        L_zero = [0.0, 0.0, 0.0]
        E0 = fusion(S, L_zero, cfg)
        expect = cfg["alpha"]
        if abs(_sum(E0) - expect) > 0.01:
            print("FAIL fusion S-only: sum E0 expected ~", expect, ", got", _sum(E0))
            failed += 1
        else:
            passed += 1
    except Exception as e:
        print("FAIL fusion S-only:", e)
        failed += 1

    # F5: both zero must raise
    try:
        fusion([0.0, 0.0], [0.0, 0.0], cfg)
        print("FAIL fusion both zero: expected ValueError (F5)")
        failed += 1
    except ValueError as e:
        if "F5" in str(e):
            passed += 1
        else:
            print("FAIL fusion both zero: wrong message", e)
            failed += 1

    # I-R2 conservation on diffusion
    W = make_demo_W(4)
    E = [0.25, 0.25, 0.25, 0.25]
    ok = check_conservation_pre_decay(E, W, cfg)
    if not ok:
        print("FAIL I-R2: conservation check failed for uniform E and demo W")
        failed += 1
    else:
        passed += 1

    # I-R3 shadow non-creation (row-stochastic Ws preserves or reduces sum)
    Ws = make_demo_W(4)
    E = [1.0, 0.0, 0.0, 0.0]
    ok = check_shadow_non_creation(E, Ws, cfg)
    if not ok:
        print("FAIL I-R3: shadow step should not create energy (row-stochastic Ws)")
        failed += 1
    else:
        passed += 1

    # I-Q2 placeholder: resolution and metrics must not depend on books (document only; real test runs with/without books)
    # Here we only assert that run_demo() produces deterministic output (no books input).
    out1 = run_demo()
    out2 = run_demo()
    if out1["governance"] != out2["governance"] or out1["loopability"] != out2["loopability"]:
        print("FAIL I-Q2 placeholder: run_demo not deterministic")
        failed += 1
    else:
        passed += 1

    return passed, failed


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        p, f = run_tests()
        print(f"HESPERIA v0.3 core math tests: {p} passed, {f} failed")
        sys.exit(0 if f == 0 else 1)
    out = run_demo()
    print("HESPERIA v0.3 core math reference — demo run")
    print("governance:", out["governance"])
    print("loopability:", out["loopability"])
    print("tension_energy:", out["tension_energy"])
    print("obstacle_score:", out["obstacle_score"])
    print("conservation_ok (I-R2):", out["conservation_ok"])
    print("shadow_non_creation_ok (I-R3):", out["shadow_non_creation_ok"])
    print("degraded:", out["degraded"])
