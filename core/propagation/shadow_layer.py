# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

# core/propagation/shadow_layer.py — HESPERIA Shadow Layer v1.0 (Core + ΓΘ Addon)
# Spec: 24_SPEC__Shadow_Layer_v1_0.txt
# Version: v0.2.1 (integrated as v0.2.0.1 → v0.2.1)
#
# Topology-preserving degraded-mode traversal: risk-based activation,
# mass decay, constrained candidate set, Γ (enter/exit) and Θ (gate, penalties, failure codes).

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Sequence

# ---------------------------------------------------------------------------
# Constants (geometry from single source: invariant_catalog)
# ---------------------------------------------------------------------------
try:
    from core.topology.invariant_catalog import AREAS, FAMILIES_PER_AREA, TOTAL_FAMILIES
except ImportError:
    from invariant_catalog import AREAS, FAMILIES_PER_AREA, TOTAL_FAMILIES

# Risk weights (sum = 1.0)
W_G = 0.40
W_T = 0.25
W_O = 0.25
W_L = 0.10

# Calibration refs for normalizing tension/obstacle (set from observed distributions if available)
T_REF = 1.0
O_REF = 1.0

# Activation thresholds
THETA_ENTER = 0.62
THETA_HARD = 0.88
THETA_EXIT = 0.52
DELTA_MIN = 0.06

# Shadow mass
SINKAGE = 0.45
SHADOW_MASS_0 = 1.0 - SINKAGE  # 0.55
LAMBDA_DECAY = 0.18
M_MIN = 0.20  # > 0 so shadow_mass ∈ (0,1] per spec §1

# Cap
K_MAX = 7

# Shadow-adjusted score penalties
ALPHA_TENSION = 0.35
BETA_OBSTACLE = 0.20

# Abuse
EPSILON_GOV = 0.02
P_ABUSE = 0.15
ABUSE_TIME_RATIO_THRESHOLD = 0.35
ABUSE_ENTER_COUNT_THRESHOLD = 3


# ---------------------------------------------------------------------------
# Failure classes (return codes)
# ---------------------------------------------------------------------------

class ShadowFailureCode(str, Enum):
    SHADOW_OK_EXIT = "SHADOW_OK_EXIT"
    SHADOW_FAIL_NO_STABLE_PATH = "SHADOW_FAIL_NO_STABLE_PATH"
    SHADOW_FAIL_INVARIANT_VIOLATION = "SHADOW_FAIL_INVARIANT_VIOLATION"
    SHADOW_FAIL_HARD_RISK = "SHADOW_FAIL_HARD_RISK"
    SHADOW_ABORT_ABUSE = "SHADOW_ABORT_ABUSE"


# ---------------------------------------------------------------------------
# Shadow metrics (output)
# ---------------------------------------------------------------------------

@dataclass
class ShadowMetrics:
    shadow_active: int = 0
    shadow_mass: float = 1.0
    shadow_time_ratio: float = 0.0
    shadow_hop_count: int = 0
    shadow_exit_success: int = 0
    shadow_abuse_flag: int = 0


# ---------------------------------------------------------------------------
# Core math (spec-compliant)
# ---------------------------------------------------------------------------

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def risk(
    governance: float,
    loopability: float,
    tension_energy: float,
    obstacle_score: float,
    *,
    w_g: float = W_G,
    w_t: float = W_T,
    w_o: float = W_O,
    w_l: float = W_L,
    t_ref: float = T_REF,
    o_ref: float = O_REF,
) -> float:
    """Normalized risk R = w_g*r_g + w_t*r_t + w_o*r_o + w_l*r_l."""
    r_g = 1.0 - clamp01(governance)
    r_t = clamp01(tension_energy / t_ref) if t_ref > 0 else 0.0
    r_o = clamp01(obstacle_score / o_ref) if o_ref > 0 else 0.0
    r_l = 1.0 - clamp01(loopability)
    return w_g * r_g + w_t * r_t + w_o * r_o + w_l * r_l


def shadow_mass_at_hop(k: int) -> float:
    """shadow_mass(k) = shadow_mass_0 * exp(-λ*k), floor m_min."""
    m = SHADOW_MASS_0 * math.exp(-LAMBDA_DECAY * k)
    return max(M_MIN, m)


def shadow_adjusted_scores(
    governance: float,
    loopability: float,
    tension_energy: float,
    obstacle_score: float,
    mass: float,
    *,
    alpha: float = ALPHA_TENSION,
    beta: float = BETA_OBSTACLE,
) -> tuple[float, float, float, float]:
    """Returns (governancê, loopabilitŷ, tension̂, obstaclê)."""
    gov_hat = governance * mass
    loop_hat = loopability * math.sqrt(mass) if mass > 0 else 0.0
    tension_hat = tension_energy * (1.0 + alpha * (1.0 - mass))
    obstacle_hat = obstacle_score * (1.0 + beta * (1.0 - mass))
    return (gov_hat, loop_hat, tension_hat, obstacle_hat)


# ---------------------------------------------------------------------------
# Family mirror φ: F → F (involutive). Default: identity.
# ---------------------------------------------------------------------------

def phi_identity(family_id: int) -> int:
    if 0 <= family_id < TOTAL_FAMILIES:
        return family_id
    return family_id


def phi_area_reflect(family_id: int) -> int:
    """Simplistic involutive map: same area, reflect family index within area."""
    if not 0 <= family_id < TOTAL_FAMILIES:
        return family_id
    area = family_id // FAMILIES_PER_AREA
    local = family_id % FAMILIES_PER_AREA
    return area * FAMILIES_PER_AREA + (FAMILIES_PER_AREA - 1 - local)


# ---------------------------------------------------------------------------
# Candidate set C = N_shadow(F) ∪ {φ(F)}, N_shadow(F) = N_base(F) ∩ N_base(φ(F))
# ---------------------------------------------------------------------------

def candidate_set_shadow(
    current_family: int,
    phi: Callable[[int], int],
    n_base: Callable[[int], Sequence[int]],
) -> set[int]:
    """Build C = N_shadow(F) ∪ {φ(F)}. n_base(F) returns iterable of neighbor family IDs."""
    mirror = phi(current_family)
    n_f = set(n_base(current_family))
    n_mirror = set(n_base(mirror))
    n_shadow = n_f & n_mirror
    c = n_shadow | {mirror}
    return c


# ---------------------------------------------------------------------------
# Γ (Gamma): enter/exit decision. Θ (Theta): abuse + penalties + failure code.
# ---------------------------------------------------------------------------

@dataclass
class ShadowLayerState:
    """Mutable run state for one traversal run."""
    shadow_active: int = 0
    shadow_mass: float = 1.0
    shadow_hop_count: int = 0
    shadow_exit_success: int = 0
    shadow_abuse_flag: int = 0
    shadow_enter_count: int = 0
    steps_in_shadow: int = 0
    total_steps: int = 0
    r_prev: float = 0.0
    failure_code: Optional[ShadowFailureCode] = None


@dataclass
class ShadowLayerInput:
    """Inputs for one step (ΓΘ)."""
    current_family: int
    governance: float
    loopability: float
    tension_energy: float
    obstacle_score: float
    base_candidates: Sequence[int]  # N_base(F) from traversal
    invariant_ok: bool = True


@dataclass
class ShadowLayerOutput:
    """Outputs after ΓΘ."""
    candidates: list[int]  # filtered/constrained candidate set
    governance_hat: float
    loopability_hat: float
    tension_hat: float
    obstacle_hat: float
    shadow_metrics: ShadowMetrics
    failure_code: Optional[ShadowFailureCode] = None
    governance_penalized: Optional[float] = None  # after Θ abuse penalty if applied


def process_step(
    state: ShadowLayerState,
    inp: ShadowLayerInput,
    *,
    phi: Callable[[int], int] = phi_identity,
    n_base: Optional[Callable[[int], Sequence[int]]] = None,
    theta_enter: float = THETA_ENTER,
    theta_hard: float = THETA_HARD,
    theta_exit: float = THETA_EXIT,
    delta_min: float = DELTA_MIN,
    k_max: int = K_MAX,
) -> ShadowLayerOutput:
    """
    Γ: compute R, enter/exit shadow, build C, update mass/hop.
    Θ: abuse detection, penalties, failure code.
    """
    r_now = risk(
        inp.governance,
        inp.loopability,
        inp.tension_energy,
        inp.obstacle_score,
    )
    state.total_steps += 1

    # Invariant violation → fail
    if not inp.invariant_ok:
        state.failure_code = ShadowFailureCode.SHADOW_FAIL_INVARIANT_VIOLATION
        state.shadow_abuse_flag = 0
        m = shadow_mass_at_hop(state.shadow_hop_count) if state.shadow_active else 1.0
        gov_h, loop_h, ten_h, obs_h = shadow_adjusted_scores(
            inp.governance, inp.loopability, inp.tension_energy, inp.obstacle_score, m
        )
        return ShadowLayerOutput(
            candidates=list(inp.base_candidates),
            governance_hat=gov_h,
            loopability_hat=loop_h,
            tension_hat=ten_h,
            obstacle_hat=obs_h,
            shadow_metrics=ShadowMetrics(
                shadow_active=state.shadow_active,
                shadow_mass=state.shadow_mass,
                shadow_time_ratio=state.steps_in_shadow / state.total_steps if state.total_steps else 0.0,
                shadow_hop_count=state.shadow_hop_count,
                shadow_exit_success=state.shadow_exit_success,
                shadow_abuse_flag=0,
            ),
            failure_code=state.failure_code,
        )

    # Γ: Enter shadow?
    if state.shadow_active == 0 and r_now >= theta_enter:
        state.shadow_active = 1
        state.shadow_mass = SHADOW_MASS_0
        state.shadow_hop_count = 0
        state.shadow_enter_count += 1
        state.r_prev = r_now

    # Build candidate set
    if n_base is None:
        n_base = lambda f: inp.base_candidates  # use provided base candidates as neighborhood
    if state.shadow_active == 1:
        state.steps_in_shadow += 1
        c = candidate_set_shadow(inp.current_family, phi, n_base)
        # C = N_shadow(F) ∪ {φ(F)}. Per-candidate "Filter C through structural invariants" (spec §5, ΓΘ C) is caller's responsibility if needed.
        candidates = list(c)
        if not candidates:
            candidates = list(inp.base_candidates)  # fallback
        state.shadow_hop_count += 1
        state.shadow_mass = shadow_mass_at_hop(state.shadow_hop_count)
        gov_hat, loop_hat, tension_hat, obstacle_hat = shadow_adjusted_scores(
            inp.governance, inp.loopability, inp.tension_energy, inp.obstacle_score, state.shadow_mass
        )
        delta_r = state.r_prev - r_now
        state.r_prev = r_now

        # Exit conditions (spec §7: exit shadow on success or fail)
        if r_now <= theta_exit and delta_r >= delta_min:
            state.shadow_active = 0
            state.shadow_exit_success = 1
            state.failure_code = ShadowFailureCode.SHADOW_OK_EXIT
        elif state.shadow_hop_count >= k_max:
            state.shadow_active = 0  # exit shadow; return to base with fail code
            state.failure_code = ShadowFailureCode.SHADOW_FAIL_NO_STABLE_PATH
        elif r_now >= theta_hard:
            state.shadow_active = 0  # hard-stop; exit shadow with fail code
            state.failure_code = ShadowFailureCode.SHADOW_FAIL_HARD_RISK
    else:
        candidates = list(inp.base_candidates)
        gov_hat = inp.governance
        loop_hat = inp.loopability
        tension_hat = inp.tension_energy
        obstacle_hat = inp.obstacle_score

    time_ratio = state.steps_in_shadow / state.total_steps if state.total_steps else 0.0

    # Θ: Abuse detection
    abuse = False
    if state.shadow_active == 1:
        if time_ratio > ABUSE_TIME_RATIO_THRESHOLD:
            abuse = True
        if state.shadow_hop_count > k_max:
            abuse = True
        if state.shadow_enter_count >= ABUSE_ENTER_COUNT_THRESHOLD:
            abuse = True
        m = state.shadow_mass
        gov_adj, _, _, _ = shadow_adjusted_scores(
            inp.governance, inp.loopability, inp.tension_energy, inp.obstacle_score, m
        )
        if gov_adj > inp.governance + EPSILON_GOV:
            abuse = True
    if abuse:
        state.shadow_abuse_flag = 1
        state.failure_code = ShadowFailureCode.SHADOW_ABORT_ABUSE
    governance_penalized = None
    if state.shadow_abuse_flag:
        governance_penalized = gov_hat * (1.0 - P_ABUSE)

    metrics = ShadowMetrics(
        shadow_active=state.shadow_active,
        shadow_mass=state.shadow_mass,
        shadow_time_ratio=time_ratio,
        shadow_hop_count=state.shadow_hop_count,
        shadow_exit_success=state.shadow_exit_success,
        shadow_abuse_flag=state.shadow_abuse_flag,
    )

    return ShadowLayerOutput(
        candidates=candidates,
        governance_hat=gov_hat,
        loopability_hat=loop_hat,
        tension_hat=tension_hat,
        obstacle_hat=obstacle_hat,
        shadow_metrics=metrics,
        failure_code=state.failure_code,
        governance_penalized=governance_penalized,
    )


# ---------------------------------------------------------------------------
# Integration: call from phase_engine / gamma_guard. Example usage:
# ---------------------------------------------------------------------------
#
# from core.propagation.shadow_layer import (
#     ShadowLayerState, ShadowLayerInput, ShadowLayerOutput, process_step,
#     risk, shadow_mass_at_hop, shadow_adjusted_scores, candidate_set_shadow,
#     phi_identity, phi_area_reflect, ShadowFailureCode,
# )
#
# state = ShadowLayerState()
# for step in traversal_steps:
#     inp = ShadowLayerInput(
#         current_family=step.family_id,
#         governance=step.governance,
#         loopability=step.loopability,
#         tension_energy=step.tension_energy,
#         obstacle_score=step.obstacle_score,
#         base_candidates=step.candidates,
#         invariant_ok=step.invariant_ok,
#     )
#     out = process_step(state, inp, phi=phi_area_reflect, n_base=your_n_base_fn)
#     # Use out.candidates, out.governance_hat, ... out.failure_code
#     if out.failure_code and out.failure_code != ShadowFailureCode.SHADOW_OK_EXIT:
#         # handle fail / hard-stop
#         break
