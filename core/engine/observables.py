# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""
Canonical field observables derived from family field state F.

Spec: spec/semantic_field_canon.md
All six scalars are defined from F, S, L_F, R_F, C (and F_next for Σ).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _square(name: str, m: np.ndarray | list) -> np.ndarray:
    arr = np.asarray(m, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        raise ValueError(f"{name} must be square, got shape {arr.shape}")
    return arr


@dataclass(frozen=True)
class FieldObservables:
    """Canonical symbols from semantic_field_canon.md §7."""

    E: float  # field energy (diffusion load, ½ F^T L F)
    K: float  # contradiction pressure (F^T C F)
    R: float  # resistance load (F^T R_F F)
    D: float  # diffusion magnitude ||L_F F||_2
    Q: float  # source alignment S^T F
    Sigma: float  # ||F_next - F||_2 (0 if F_next is None)

    def as_dict(self) -> dict[str, float]:
        return {
            "E": self.E,
            "K": self.K,
            "R": self.R,
            "D": self.D,
            "Q": self.Q,
            "Sigma": self.Sigma,
        }

    def as_dict_aliases(self) -> dict[str, float]:
        """Names aligned with timeline / JSON consumers."""
        d = self.as_dict()
        d["field_energy_E"] = self.E
        d["contradiction_pressure_K"] = self.K
        d["resistance_load_R"] = self.R
        d["diffusion_magnitude_D"] = self.D
        d["source_alignment_Q"] = self.Q
        d["stability_sigma_l2"] = self.Sigma
        return d


def compute_field_observables(
    F: np.ndarray | list[float],
    S: np.ndarray | list[float],
    L_F: np.ndarray,
    R_F: np.ndarray,
    C: np.ndarray,
    *,
    F_next: np.ndarray | list[float] | None = None,
    F_for_Q: np.ndarray | list[float] | None = None,
) -> FieldObservables:
    """
    Compute E, K, R, D, Q, Σ per canonical spec.

    - E, K, R, D use **F** (current field state).
    - Q = S^T F_eval; default F_eval = F_for_Q or F.
    - Σ = ||F_next - F|| if F_next given, else 0.0.
    """
    f = np.asarray(F, dtype=np.float64).reshape(-1)
    s = np.asarray(S, dtype=np.float64).reshape(-1)
    if s.shape[0] != f.shape[0]:
        raise ValueError(f"S length {s.shape[0]} != F length {f.shape[0]}")
    l_f = _square("L_F", L_F)
    r_f = _square("R_F", R_F)
    c = _square("C", C)
    n = f.shape[0]
    for name, m in (("L_F", l_f), ("R_F", r_f), ("C", c)):
        if m.shape != (n, n):
            raise ValueError(f"{name} shape {m.shape} != ({n},{n})")

    lf = l_f @ f
    E = 0.5 * float(f @ lf)
    K = float(f @ (c @ f))
    R = float(f @ (r_f @ f))
    D = float(np.linalg.norm(lf, ord=2))
    f_q = np.asarray(F_for_Q, dtype=np.float64).reshape(-1) if F_for_Q is not None else f
    if f_q.shape[0] != n:
        raise ValueError("F_for_Q length must match F")
    Q = float(s @ f_q)

    if F_next is None:
        sigma = 0.0
    else:
        fn = np.asarray(F_next, dtype=np.float64).reshape(-1)
        if fn.shape[0] != n:
            raise ValueError("F_next length must match F")
        sigma = float(np.linalg.norm(fn - f, ord=2))

    return FieldObservables(E=E, K=K, R=R, D=D, Q=Q, Sigma=sigma)


def observables_from_timestep(
    F_t: np.ndarray | list[float],
    F_t_plus_1: np.ndarray | list[float],
    S: np.ndarray | list[float],
    L_F: np.ndarray,
    R_F: np.ndarray,
    C: np.ndarray,
    *,
    Q_on: str = "next",
) -> FieldObservables:
    """
    Observables for a single step: Σ uses F_{t+1} - F_t.

    Q_on: 'next' → Q = S^T F_{t+1}; 'prev' → S^T F_t; 'average' → mean of both.
    """
    ft = np.asarray(F_t, dtype=np.float64).reshape(-1)
    fn = np.asarray(F_t_plus_1, dtype=np.float64).reshape(-1)
    if Q_on == "next":
        f_q = fn
    elif Q_on == "prev":
        f_q = ft
    elif Q_on == "average":
        f_q = 0.5 * (ft + fn)
    else:
        raise ValueError("Q_on must be 'next', 'prev', or 'average'")
    return compute_field_observables(
        ft, S, L_F, R_F, C, F_next=fn, F_for_Q=f_q,
    )


__all__ = [
    "FieldObservables",
    "compute_field_observables",
    "observables_from_timestep",
]
