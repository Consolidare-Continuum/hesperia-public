# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def sat(x: float) -> float:
    """Bounded saturation v0.1 — KSI spec section 4.10."""
    return min(1.0, max(0.0, x))


@dataclass(frozen=True, slots=True)
class PhiEParams:
    """Semantic transfer parameters for one directed edge (KSI section 4)."""

    a_i: float
    w_e: float
    r_e: float
    q_e: float
    s_e: float
    c_e: float
    p_e: float
    d_e: float
    k_e: float


def phi_e_raw(params: PhiEParams) -> float:
    return (
        params.a_i
        * params.w_e
        * params.r_e
        * params.q_e
        * params.s_e
        * params.c_e
        * params.p_e
        * params.d_e
        - params.k_e
    )


def phi_e(params: PhiEParams) -> float:
    """Expected edge contribution Phi_e in [0, 1] after sat() — KSI section 3.2."""
    return sat(phi_e_raw(params))


def phi_e_trace(params: PhiEParams) -> dict[str, float]:
    raw = phi_e_raw(params)
    return {
        "a_i": params.a_i,
        "w_e": params.w_e,
        "r_e": params.r_e,
        "q_e": params.q_e,
        "s_e": params.s_e,
        "c_e": params.c_e,
        "p_e": params.p_e,
        "d_e": params.d_e,
        "k_e": params.k_e,
        "phi_raw": raw,
        "phi_sat": sat(raw),
    }


def default_ksi_data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "assets" / "data" / "ksi"


def load_relation_type_coefficients(path: Path | None = None) -> Mapping[str, float]:
    import json

    if path is None:
        path = default_ksi_data_dir() / "relation_type_coefficients_v01.json"
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data["coefficients"]


def r_e_for_type(relation_type: str, coefficients: Mapping[str, float] | None = None) -> float:
    table = coefficients if coefficients is not None else load_relation_type_coefficients()
    return float(table.get(relation_type, table.get("*", 0.5)))
