# HESPERIA — RAD. SEMANTIC_FIELD_EQUATIONS_v1 — calibration + E2E bundle.
# Core stepping: hesperia.extensions.dynamics.equations (explicit L_F, R_F, C).
# See specs/dynamics/semantic_field_dynamics.md (canonical)

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from . import equations as eq
from core.topology.invariant_catalog import (
    AREAS as NUM_AREAS,
    FAMILIES_PER_AREA,
    TOTAL_FAMILIES as NUM_FAMILIES,
)

SPEC_ID = "SEMANTIC_FIELD_EQUATIONS_v1"

# When True, bundle output notes that matrices were not caller-supplied.
STUB_MATRICES_PROVENANCE = "stub_canonical_ring_DEV_ONLY_explicit_registry_required_for_production"

# Legacy unit tests only — production must use ``core.engine.matrix_loader.load_production_matrices``.
_STUB_MATRICES_ENV = "HESPERIA_SEMANTIC_FIELD_STUB_MATRICES"


def _stub_matrices_allowed() -> bool:
    return os.environ.get(_STUB_MATRICES_ENV) == "1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_calibration_path() -> Path:
    return _repo_root() / "assets" / "calibration" / "semantic_field_equations_v1.json"


@dataclass(frozen=True)
class SemanticFieldParamsV1:
    """Versioned parameters; load from calibration JSON. Maps to equations.SemanticFieldParams."""

    alpha: float = 0.15
    beta: float = 0.08
    gamma: float = 0.12
    delta: float = 0.25
    mu: float = 0.01
    dt: float = 0.05
    epsilon: float = 1e-4
    tau: float = 0.02
    resistance_uniform: float = 1.0
    production_clip: bool = True
    signed_source_experimental: bool = False
    spec_id: str = SPEC_ID
    calibration_path: str = ""

    def to_metadata(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "alpha": self.alpha,
            "beta": self.beta,
            "gamma": self.gamma,
            "delta": self.delta,
            "mu": self.mu,
            "dt": self.dt,
            "epsilon": self.epsilon,
            "tau": self.tau,
            "resistance_uniform": self.resistance_uniform,
            "production_clip": self.production_clip,
            "signed_source_experimental": self.signed_source_experimental,
            "calibration_path": self.calibration_path or None,
        }

    def to_equations_params(self) -> eq.SemanticFieldParams:
        return eq.SemanticFieldParams(
            alpha=self.alpha,
            beta=self.beta,
            gamma=self.gamma,
            delta=self.delta,
            mu=self.mu,
            dt=self.dt,
            epsilon=self.epsilon,
            tau=self.tau,
            clip_mode=self.production_clip,
        )


def load_semantic_field_params_v1(path: Path | str | None = None) -> SemanticFieldParamsV1:
    p = Path(path) if path else default_calibration_path()
    raw = json.loads(p.read_text(encoding="utf-8"))
    pr = raw.get("parameters") or raw
    return SemanticFieldParamsV1(
        alpha=float(pr["alpha"]),
        beta=float(pr["beta"]),
        gamma=float(pr["gamma"]),
        delta=float(pr["delta"]),
        mu=float(pr["mu"]),
        dt=float(pr["dt"]),
        epsilon=float(pr["epsilon"]),
        tau=float(pr["tau"]),
        resistance_uniform=float(pr.get("resistance_uniform", 1.0)),
        production_clip=bool(pr.get("production_clip", True)),
        signed_source_experimental=bool(pr.get("signed_source_experimental", False)),
        spec_id=str(raw.get("spec_id", SPEC_ID)),
        calibration_path=str(p.resolve()),
    )


def family_area_map() -> np.ndarray:
    """A(m) = area index 0..11 for family m 0..287."""
    return eq.build_identity_family_mapping(family_count=NUM_FAMILIES)


def build_family_adjacency_from_sets(adjacency: Sequence[set[int]]) -> np.ndarray:
    """
    Symmetric weighted adjacency W_F from neighbor sets (weight 1 per edge).
    Caller supplies topology explicitly (e.g. from registry).
    """
    if len(adjacency) != NUM_FAMILIES:
        raise ValueError(f"adjacency must have length {NUM_FAMILIES}, got {len(adjacency)}")
    w = np.zeros((NUM_FAMILIES, NUM_FAMILIES), dtype=np.float64)
    for i, neigh in enumerate(adjacency):
        for j in neigh:
            if 0 <= j < NUM_FAMILIES and i != j:
                w[i, j] = 1.0
                w[j, i] = 1.0
    return w


def build_family_adjacency_weighted(
    edges: Iterable[tuple[int, int, float]],
    *,
    n: int = NUM_FAMILIES,
    symmetric: bool = True,
) -> np.ndarray:
    """Build W from (i, j, weight); explicit edge list from config."""
    w = np.zeros((n, n), dtype=np.float64)
    for i, j, wt in edges:
        if wt < 0:
            raise ValueError("edge weights must be non-negative")
        if i == j or not (0 <= i < n and 0 <= j < n):
            continue
        w[i, j] += wt
        if symmetric:
            w[j, i] += wt
    return w


def build_family_laplacian(w_f: np.ndarray) -> np.ndarray:
    """L_F from explicit weighted adjacency W_F (via equations)."""
    return eq.build_family_laplacian(np.asarray(w_f, dtype=np.float64))


def build_resistance_matrix(
    r: np.ndarray | float | None = None,
    *,
    uniform: float = 1.0,
) -> np.ndarray:
    """Diagonal R_F from explicit per-family vector or uniform scalar."""
    if r is None:
        diag = np.full(NUM_FAMILIES, float(uniform), dtype=np.float64)
    else:
        arr = np.asarray(r, dtype=np.float64).ravel()
        if arr.size == 1:
            diag = np.full(NUM_FAMILIES, float(arr[0]), dtype=np.float64)
        elif arr.size == NUM_FAMILIES:
            diag = arr.copy()
        else:
            raise ValueError(f"resistance length must be 1 or {NUM_FAMILIES}, got {arr.size}")
    if (diag < 0).any():
        raise ValueError("resistance diagonal must be non-negative")
    return eq.build_resistance_matrix(diag)


def build_contradiction_matrix(
    c: np.ndarray | None = None,
    *,
    n: int = NUM_FAMILIES,
) -> np.ndarray:
    """C from explicit matrix, or zeros. Production C should come from TRIZ/registry."""
    if c is None:
        return np.zeros((n, n), dtype=np.float64)
    return eq.build_contradiction_matrix(np.asarray(c, dtype=np.float64))


def _documents_for_equations(documents: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in documents:
        vec = d.get("source_vector") or d.get("s_288") or d.get("S")
        if vec is None:
            continue
        item: dict[str, Any] = {"source_vector": list(vec)}
        if "weight" in d:
            item["weight"] = d["weight"]
        item["quality"] = float(d.get("quality", d.get("q", 1.0)))
        item["mass"] = float(d.get("mass", 1.0))
        if "timestamp" in d or "t" in d:
            item["timestamp"] = float(d.get("timestamp", d.get("t", 0.0)))
        out.append(item)
    return out


def aggregate_source_vectors(
    documents: Sequence[Mapping[str, Any]],
    *,
    t_ref: float = 0.0,
    signed_allowed: bool = False,
    params: SemanticFieldParamsV1 | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Aggregate document sources using equations + calibration mu."""
    prm = params or load_semantic_field_params_v1()
    if prm.signed_source_experimental or signed_allowed:
        pass
    docs = _documents_for_equations(documents)
    for i, d in enumerate(documents):
        vec = d.get("source_vector") or d.get("s_288") or d.get("S")
        if vec is None:
            continue
        arr = np.asarray(vec, dtype=np.float64).reshape(NUM_FAMILIES)
        if not prm.signed_source_experimental and not signed_allowed and (arr < -1e-15).any():
            raise ValueError("source vectors must be non-negative unless signed_source_experimental")
    ep = prm.to_equations_params()
    s_total = eq.aggregate_sources_with_params(docs, family_count=NUM_FAMILIES, params=ep, now_t=t_ref)
    meta_weights: list[float] = []
    for d in docs:
        w = float(d.get("weight", 1.0)) * float(d.get("quality", 1.0)) * float(d.get("mass", 1.0))
        if t_ref is not None and ep.mu > 0.0 and "timestamp" in d:
            w *= float(np.exp(-ep.mu * max(0.0, t_ref - float(d["timestamp"]))))
        meta_weights.append(w)
    return s_total, {"document_weights": meta_weights, "mu": prm.mu, "t_ref": t_ref}


def source_from_hits_normalized(hits: Sequence[float] | Sequence[int]) -> np.ndarray:
    """Dict A/B pipeline proxy: non-negative hits → normalized S^(d)."""
    h = np.asarray(hits, dtype=np.float64).reshape(NUM_FAMILIES)
    h = np.maximum(h, 0.0)
    t = h.sum()
    if t <= 0:
        return np.full(NUM_FAMILIES, 1.0 / NUM_FAMILIES, dtype=np.float64)
    return h / t


def _observables_v1_aliases(o: dict[str, float]) -> dict[str, float]:
    """Spec §12 names + equations canonical names."""
    return {
        **o,
        "propagation_velocity_v": o["propagation_velocity"],
        "contradiction_load_K": o["contradiction_load"],
        "diffusion_load_D": o["diffusion_load"],
        "resistance_load_R": o["resistance_load"],
        "source_alignment_Q": o["source_alignment"],
        "stability_sigma": o["stability_score"],
    }


def step_field_euler(
    f_t: np.ndarray,
    s_t: np.ndarray,
    l_f: np.ndarray,
    r_f: np.ndarray,
    c: np.ndarray,
    *,
    params: SemanticFieldParamsV1 | None = None,
    dt: float | None = None,
    clip_01: bool | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """One Euler step via equations.step_field."""
    p = params or load_semantic_field_params_v1()
    ep = p.to_equations_params()
    if dt is not None or clip_01 is not None:
        ep = eq.SemanticFieldParams(
            alpha=ep.alpha,
            beta=ep.beta,
            gamma=ep.gamma,
            delta=ep.delta,
            mu=ep.mu,
            dt=float(dt) if dt is not None else ep.dt,
            epsilon=ep.epsilon,
            tau=ep.tau,
            clip_mode=p.production_clip if clip_01 is None else bool(clip_01),
        )
    f_t = np.asarray(f_t, dtype=np.float64).reshape(NUM_FAMILIES)
    s_t = np.asarray(s_t, dtype=np.float64).reshape(NUM_FAMILIES)
    if not p.signed_source_experimental and (s_t < -1e-15).any():
        raise ValueError("S must be non-negative in production-safe mode")
    res = eq.step_field(f_t, s_t, l_f, r_f, c, ep)
    d_norm = res.observables["delta_norm_l2"]
    return res.field_next, {
        "delta_f_norm_l2": d_norm,
        "contradiction_pressure": res.pressure_vector.copy(),
        "contradiction_pressure_l1": res.observables["pressure_norm_l1"],
        "deriv_l2": float(np.linalg.norm(res.delta_vector / max(ep.dt, 1e-15))),
    }


def compute_field_energy_linear(
    f: np.ndarray,
    s: np.ndarray,
    l_f: np.ndarray,
    r_f: np.ndarray,
    c: np.ndarray,
    *,
    params: SemanticFieldParamsV1 | None = None,
) -> float:
    p = (params or load_semantic_field_params_v1()).to_equations_params()
    return eq.compute_energy(f, s, l_f, r_f, c, p)


def compute_observables(
    f_t: np.ndarray,
    f_next: np.ndarray,
    s_t: np.ndarray,
    l_f: np.ndarray,
    r_f: np.ndarray,
    c: np.ndarray,
    *,
    dt: float,
    params: SemanticFieldParamsV1 | None = None,
) -> dict[str, float]:
    p = params or load_semantic_field_params_v1()
    ep = eq.SemanticFieldParams(
        alpha=p.alpha,
        beta=p.beta,
        gamma=p.gamma,
        delta=p.delta,
        mu=p.mu,
        dt=dt,
        epsilon=p.epsilon,
        tau=p.tau,
        clip_mode=p.production_clip,
    )
    return _observables_v1_aliases(eq.compute_observables(f_t, f_next, s_t, l_f, r_f, c, ep))


def project_family_to_area(f: np.ndarray) -> np.ndarray:
    """Area aggregation from explicit 12×24 layout."""
    f = np.asarray(f, dtype=np.float64).reshape(NUM_FAMILIES)
    m = eq.build_identity_family_mapping(family_count=NUM_FAMILIES)
    return eq.aggregate_family_to_area(f, m, area_count=NUM_AREAS)


def compute_convergence_metrics(
    f_t: np.ndarray,
    f_next: np.ndarray,
    c: np.ndarray,
    *,
    params: SemanticFieldParamsV1 | None = None,
) -> dict[str, Any]:
    p = (params or load_semantic_field_params_v1()).to_equations_params()
    conv = eq.compute_convergence_metrics(f_t, f_next, c, p)
    return {
        "numerically_stable": conv["converged_numerical"],
        "contradiction_stable": conv["converged_contradiction"],
        "delta_f_norm_l2": conv["delta_norm_l2"],
        "contradiction_pressure_l1": conv["pressure_norm_l1"],
    }


def run_field_timeline(
    f0: np.ndarray,
    s_sequence: Sequence[np.ndarray] | np.ndarray,
    l_f: np.ndarray,
    r_f: np.ndarray,
    c: np.ndarray,
    *,
    params: SemanticFieldParamsV1 | None = None,
    n_steps: int | None = None,
) -> dict[str, Any]:
    p = params or load_semantic_field_params_v1()
    ep = p.to_equations_params()
    f = np.asarray(f0, dtype=np.float64).reshape(NUM_FAMILIES).copy()
    seq = np.asarray(s_sequence, dtype=np.float64)
    if seq.ndim == 1:
        seq = np.tile(seq, (n_steps or 1, 1))
    steps = seq.shape[0] if n_steps is None else min(int(n_steps), seq.shape[0])
    timeline: list[dict[str, Any]] = []

    for t in range(steps):
        s_t = seq[t]
        e_before = eq.compute_energy(f, s_t, l_f, r_f, c, ep)
        res = eq.step_field(f, s_t, l_f, r_f, c, ep)
        f_n = res.field_next
        obs = _observables_v1_aliases(res.observables)
        stab = {
            "numerically_stable": res.converged_numerical,
            "contradiction_stable": res.converged_contradiction,
            "delta_norm_l2": res.observables["delta_norm_l2"],
            "pressure_norm_l1": res.observables["pressure_norm_l1"],
        }
        timeline.append(
            {
                "step": t,
                "field_state": [round(float(x), 8) for x in f.tolist()],
                "field_state_next": [round(float(x), 8) for x in f_n.tolist()],
                "field_energy": round(e_before, 8),
                "field_observables": {k: round(float(v), 8) for k, v in obs.items()},
                "field_stability": stab,
                "field_area_projection": [round(float(x), 8) for x in project_family_to_area(f).tolist()],
                "field_source_vector": [round(float(x), 8) for x in s_t.tolist()],
            }
        )
        f = f_n

    return {
        "spec_id": SPEC_ID,
        "params_metadata": p.to_metadata(),
        "field_timeline": timeline,
        "final_field": [round(float(x), 8) for x in f.tolist()],
    }


def build_stub_matrices_dev_only(
    adjacency: Sequence[set[int]] | None = None,
    contradiction: np.ndarray | None = None,
    *,
    resistance_diag: np.ndarray | float | None = None,
) -> dict[str, np.ndarray]:
    """
    **DEV / tests only.** Builds L_F, R_F, C from the canonical ring stub adjacency unless
    caller passes explicit adjacency. Production must load matrices via
    ``core.engine.matrix_loader.load_production_matrices``.
    """
    if not _stub_matrices_allowed():
        raise RuntimeError(
            "Stub matrices are forbidden outside dev/tests. "
            "Use core.engine.matrix_loader.load_production_matrices(). "
            f"For legacy tests only, set {_STUB_MATRICES_ENV}=1."
        )
    from core.layers.layer_2 import build_canonical_stub_adjacency

    adj = adjacency or build_canonical_stub_adjacency(NUM_FAMILIES, NUM_AREAS)
    w_f = build_family_adjacency_from_sets(adj)
    l_f = eq.build_family_laplacian(w_f)
    pr = load_semantic_field_params_v1()
    if resistance_diag is not None:
        r_f = build_resistance_matrix(r=resistance_diag)
    else:
        r_f = build_resistance_matrix(uniform=pr.resistance_uniform)
    c = build_contradiction_matrix(contradiction)
    return {"W_F": w_f, "L_F": l_f, "R_F": r_f, "C": c}


def build_default_matrices(
    adjacency: Sequence[set[int]] | None = None,
    contradiction: np.ndarray | None = None,
    *,
    resistance_diag: np.ndarray | float | None = None,
) -> dict[str, np.ndarray]:
    """
    **Forbidden in production** — alias for :func:`build_stub_matrices_dev_only`.

    Governed runs must call ``load_production_matrices`` instead.
    """
    if not _stub_matrices_allowed():
        raise RuntimeError(
            "build_default_matrices() is not allowed in production. "
            "Use core.engine.matrix_loader.load_production_matrices(). "
            f"For legacy tests only, set {_STUB_MATRICES_ENV}=1."
        )
    return build_stub_matrices_dev_only(
        adjacency=adjacency, contradiction=contradiction, resistance_diag=resistance_diag
    )


def semantic_field_e2e_bundle(
    *,
    f0: np.ndarray | None = None,
    source_288: np.ndarray | Sequence[float],
    hits_as_source: bool = False,
    documents: Sequence[Mapping[str, Any]] | None = None,
    t_ref: float = 0.0,
    n_steps: int = 1,
    matrices: Mapping[str, np.ndarray] | None = None,
    params: SemanticFieldParamsV1 | None = None,
) -> dict[str, Any]:
    """
    E2E JSON bundle. Pass ``matrices`` with keys ``L_F``, ``R_F``, ``C`` from registry.
    If omitted, production matrices are loaded from ``assets/matrices/production/``.
    """
    p = params or load_semantic_field_params_v1()
    if matrices is not None:
        mats = dict(matrices)
        prov = "caller_supplied"
    else:
        from core.engine.matrix_loader import load_production_matrices

        loaded = load_production_matrices()
        mats = {
            "L_F": loaded["L_F"],
            "R_F": loaded["R_F"],
            "C": loaded["C_F"],
        }
        prov = f"production_bundle_{loaded['bundle_version']}"
    l_f, r_f, c = mats["L_F"], mats["R_F"], mats["C"]

    if documents is not None:
        s_agg, s_meta = aggregate_source_vectors(
            list(documents),
            t_ref=t_ref,
            signed_allowed=p.signed_source_experimental,
            params=p,
        )
        s_use = s_agg
        source_meta = {**s_meta, "matrices_provenance": prov}
    elif hits_as_source:
        s_use = source_from_hits_normalized(source_288)
        source_meta = {"mode": "hits_normalized", "matrices_provenance": prov}
    else:
        s_use = np.asarray(source_288, dtype=np.float64).reshape(NUM_FAMILIES)
        source_meta = {"mode": "explicit", "matrices_provenance": prov}

    f_start = f0 if f0 is not None else np.full(NUM_FAMILIES, 1.0 / NUM_FAMILIES, dtype=np.float64)
    f_start = np.asarray(f_start, dtype=np.float64).reshape(NUM_FAMILIES)

    s_seq = np.tile(s_use, (max(1, n_steps), 1))
    tl = run_field_timeline(f_start, s_seq, l_f, r_f, c, params=p, n_steps=max(1, n_steps))
    last = tl["field_timeline"][-1] if tl["field_timeline"] else {}

    out: dict[str, Any] = {
        "spec_id": SPEC_ID,
        "matrices_provenance": prov,
        "field_state": last.get("field_state", [round(float(x), 8) for x in f_start.tolist()]),
        "field_state_next": last.get("field_state_next", []),
        "field_energy": last.get("field_energy"),
        "field_observables": last.get("field_observables"),
        "field_stability": last.get("field_stability"),
        "field_area_projection": last.get("field_area_projection"),
        "field_source_vector": [round(float(x), 8) for x in s_use.tolist()],
        "field_timeline": tl["field_timeline"] if n_steps > 1 else None,
        "params_metadata": p.to_metadata(),
        "source_aggregation": source_meta,
    }
    if n_steps <= 1:
        del out["field_timeline"]
    return out


__all__ = [
    "SPEC_ID",
    "STUB_MATRICES_PROVENANCE",
    "NUM_FAMILIES",
    "NUM_AREAS",
    "SemanticFieldParamsV1",
    "load_semantic_field_params_v1",
    "default_calibration_path",
    "family_area_map",
    "build_family_adjacency_from_sets",
    "build_family_adjacency_weighted",
    "build_family_laplacian",
    "build_resistance_matrix",
    "build_contradiction_matrix",
    "build_stub_matrices_dev_only",
    "aggregate_source_vectors",
    "source_from_hits_normalized",
    "step_field_euler",
    "compute_field_energy_linear",
    "compute_observables",
    "project_family_to_area",
    "compute_convergence_metrics",
    "run_field_timeline",
    "build_default_matrices",
    "semantic_field_e2e_bundle",
]
