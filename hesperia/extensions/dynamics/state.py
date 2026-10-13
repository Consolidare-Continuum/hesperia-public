# HESPERIA — RAD. Ethan dynamics state — Phase 1 (L6–L9) + Phase 2 (L5 family).
# See specs/dynamics/ETHAN_SEMANTIC_FIELD_DYNAMICS_SPEC.md §A.6.

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from core.topology.invariant_catalog import (
    AREAS as NUM_AREAS,
    FAMILIES_PER_AREA,
    TOTAL_FAMILIES as NUM_FAMILIES,
)

STATE_VERSION = 4


def _default_f_f() -> np.ndarray:
    return np.full(NUM_FAMILIES, 1.0 / NUM_FAMILIES, dtype=np.float64)


def _default_p_family() -> np.ndarray:
    return np.zeros(NUM_FAMILIES, dtype=np.float64)


@dataclass
class FieldDynamicsState:
    """
    L4 (Phase 3): hex_x, hex_p — sparse active family-proxy cells (JSON keys str family_id).
    L5: f_f, p_family; L6–L7: area_a, p_a; L9: stab.
    """

    t: int
    area_a: np.ndarray
    p_a: np.ndarray
    stab: float
    concept_mass: float = 0.0
    f_f: np.ndarray = field(default_factory=_default_f_f)
    p_family: np.ndarray = field(default_factory=_default_p_family)
    hex_x: dict[str, float] = field(default_factory=dict)
    hex_p: dict[str, float] = field(default_factory=dict)
    l8_cluster_mass_prev: dict[str, float] = field(default_factory=dict)
    version: int = STATE_VERSION

    def __post_init__(self) -> None:
        self.area_a = np.asarray(self.area_a, dtype=np.float64).reshape(NUM_AREAS)
        self.p_a = np.asarray(self.p_a, dtype=np.float64).reshape(NUM_AREAS)
        self.f_f = np.asarray(self.f_f, dtype=np.float64).reshape(NUM_FAMILIES)
        self.p_family = np.asarray(self.p_family, dtype=np.float64).reshape(NUM_FAMILIES)

    @staticmethod
    def initial_uniform() -> FieldDynamicsState:
        a = np.full(NUM_AREAS, 1.0 / NUM_AREAS, dtype=np.float64)
        return FieldDynamicsState(
            t=0,
            area_a=a,
            p_a=np.zeros(NUM_AREAS, dtype=np.float64),
            stab=1.0,
            f_f=_default_f_f(),
            p_family=_default_p_family(),
            hex_x={},
            hex_p={},
            l8_cluster_mass_prev={},
        )

    def to_serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d["area_a"] = [float(x) for x in self.area_a.tolist()]
        d["p_a"] = [float(x) for x in self.p_a.tolist()]
        d["f_f"] = [float(x) for x in self.f_f.tolist()]
        d["p_family"] = [float(x) for x in self.p_family.tolist()]
        d["hex_x"] = {str(k): float(v) for k, v in sorted(self.hex_x.items(), key=lambda x: int(x[0]))}
        d["hex_p"] = {str(k): float(v) for k, v in sorted(self.hex_p.items(), key=lambda x: int(x[0]))}
        d["l8_cluster_mass_prev"] = {
            str(k): float(v) for k, v in sorted(self.l8_cluster_mass_prev.items(), key=lambda x: x[0])
        }
        return d

    @staticmethod
    def from_serializable(d: dict[str, Any]) -> FieldDynamicsState:
        f_f = d.get("f_f")
        p_fam = d.get("p_family")
        if not f_f or len(f_f) != NUM_FAMILIES:
            f_f = _default_f_f().tolist()
        if not p_fam or len(p_fam) != NUM_FAMILIES:
            p_fam = _default_p_family().tolist()
        hx = d.get("hex_x") if isinstance(d.get("hex_x"), dict) else {}
        hp = d.get("hex_p") if isinstance(d.get("hex_p"), dict) else {}
        hx = {str(k): float(v) for k, v in hx.items()}
        hp = {str(k): float(v) for k, v in hp.items()}
        l8 = d.get("l8_cluster_mass_prev") if isinstance(d.get("l8_cluster_mass_prev"), dict) else {}
        l8 = {str(k): float(v) for k, v in l8.items()}
        return FieldDynamicsState(
            t=int(d["t"]),
            area_a=np.asarray(d["area_a"], dtype=np.float64),
            p_a=np.asarray(d["p_a"], dtype=np.float64),
            stab=float(d["stab"]),
            concept_mass=float(d.get("concept_mass", 0.0)),
            f_f=np.asarray(f_f, dtype=np.float64),
            p_family=np.asarray(p_fam, dtype=np.float64),
            hex_x=hx,
            hex_p=hp,
            l8_cluster_mass_prev=l8,
            version=int(d.get("version", STATE_VERSION)),
        )


@dataclass(frozen=True)
class Phase1Theta:
    """L6–L7–L9 knobs (compact H6, H7, H9)."""

    lambda_a: float = 0.35
    gamma_f: float = 0.4
    gamma_q: float = 0.15
    gamma_p: float = 0.08
    mu_a: float = 0.4
    delta_a: float = 0.12
    rho_a: float = 0.02
    lambda_c: float = 0.3
    alpha_in: float = 0.25


@dataclass(frozen=True)
class Phase2Theta:
    """L5 compact H4, H5 + blend to L6 (Ethan §A.4)."""

    lambda_f: float = 0.35
    beta_x: float = 0.42
    beta_intra: float = 0.08
    beta_area: float = 0.1
    beta_pf: float = 0.06
    mu_f: float = 0.4
    delta_f: float = 0.1
    rho_f: float = 0.002
    area_hit_weight: float = 0.52


@dataclass(frozen=True)
class Phase4Theta:
    """L8 cluster gravity coupling (Ethan §H8 proxy)."""

    gravity_epsilon: float = 0.055
    tau_front: float = 0.085
    ephemeral_cap: int = 96


@dataclass(frozen=True)
class Phase3Theta:
    """L4 active subgraph (family-proxy hex cells). Ethan Part B Phase C — capped, not full 72k."""

    hex_cap: int = 128
    lambda_h: float = 0.32
    theta_c: float = 0.45
    theta_d: float = 0.18
    theta_p: float = 0.06
    mu_h: float = 0.38
    delta_h: float = 0.08
    rho_h: float = 0.001
    hex_hit_blend: float = 0.48
