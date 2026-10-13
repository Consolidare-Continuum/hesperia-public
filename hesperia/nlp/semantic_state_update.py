# HESPERIA — Deterministic semantic state propagation (H_total over concepts).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_H_TOTAL = (
    _REPO_ROOT
    / "assets"
    / "data"
    / "engine_dynamics_v060"
    / "semantic_dynamics"
    / "h_total_concepts.json"
)


def default_h_total_path() -> Path:
    return _DEFAULT_H_TOTAL


def saturate_signed(x: float, k: float = 1.2) -> float:
    if x == 0.0:
        return 0.0
    return math.copysign(1.0 - math.exp(-k * abs(x)), x)


def normalize_l1_abs(vec: dict[str, float]) -> dict[str, float]:
    denom = sum(abs(v) for v in vec.values())
    norm = max(denom, 1.0)
    return {k: v / norm for k, v in vec.items()}


def prune_small(vec: dict[str, float], eps: float = 0.03) -> dict[str, float]:
    return {k: (0.0 if abs(v) < eps else v) for k, v in vec.items()}


def vectorize_evidence(
    evidence_t: Mapping[str, float],
    concept_index: list[str],
) -> dict[str, float]:
    return {cid: float(evidence_t.get(cid, 0.0)) for cid in concept_index}


def _nonzero_count(vec: Mapping[str, float]) -> int:
    return sum(1 for v in vec.values() if abs(float(v)) >= 1e-15)


def _top_entries(vec: Mapping[str, float], *, k: int = 8) -> list[list[float | str]]:
    items = sorted(vec.items(), key=lambda it: abs(float(it[1])), reverse=True)[:k]
    return [[str(a), round(float(b), 6)] for a, b in items if abs(float(b)) >= 1e-15]


@lru_cache(maxsize=4)
def load_h_total(path: str | None = None) -> dict[str, Any]:
    p = Path(path) if path else _DEFAULT_H_TOTAL
    if not p.is_file():
        raise FileNotFoundError(f"missing H_total operator file: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("H_total payload must be a JSON object")
    return data


def validate_h_total_symmetry_and_bounds(
    h_total: Mapping[str, Any],
    *,
    tol: float = 1e-9,
) -> tuple[bool, bool, dict[str, Any]]:
    """Return (symmetric_ok, bounded_ok, detail)."""
    br = h_total.get("build_rules") or {}
    lo = float(br.get("bounded_min", -1.0))
    hi = float(br.get("bounded_max", 1.0))
    concept_index = [str(x) for x in (h_total.get("concept_index") or [])]
    index_set = set(concept_index)
    diag = h_total.get("diagonal") or {}
    edges = h_total.get("edges") or []

    bounded_ok = True
    for cid in concept_index:
        if cid not in diag:
            continue
        v = float(diag[cid])
        if v < lo - tol or v > hi + tol:
            bounded_ok = False
            break

    pair_vals: dict[tuple[str, str], float] = {}
    symmetric_ok = True
    if isinstance(edges, list):
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            a = str(edge.get("a", ""))
            b = str(edge.get("b", ""))
            if not a or not b or a == b:
                continue
            if a not in index_set or b not in index_set:
                symmetric_ok = False
                continue
            key = (a, b) if a < b else (b, a)
            val = float(edge.get("value", 0.0))
            if val < lo - tol or val > hi + tol:
                bounded_ok = False
            prev = pair_vals.get(key)
            if prev is not None and abs(prev - val) > tol:
                symmetric_ok = False
            else:
                pair_vals[key] = val

    detail = {
        "concept_count": len(concept_index),
        "edge_count": len(edges) if isinstance(edges, list) else 0,
        "bounded_range": [lo, hi],
    }
    return symmetric_ok, bounded_ok, detail


def propagate_state(
    psi_prev: Mapping[str, float],
    evidence_t: Mapping[str, float],
    h_total: Mapping[str, Any],
    *,
    alpha: float = 0.7,
    sat_k: float = 1.2,
    prune_eps: float = 0.03,
) -> tuple[dict[str, float], dict[str, float]]:
    """
    One-step ψ update: raw = H·ψ_prev + α·e_t, then saturate → prune → L1-abs normalize.

    Returns (psi_next, raw_pre_saturate).
    """
    concept_ids = [str(x) for x in (h_total.get("concept_index") or [])]
    diag = h_total.get("diagonal") or {}
    edges = h_total.get("edges") or []

    raw: dict[str, float] = {cid: 0.0 for cid in concept_ids}

    for cid in concept_ids:
        raw[cid] += float(diag.get(cid, 0.0)) * float(psi_prev.get(cid, 0.0))

    if isinstance(edges, list):
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            a = str(edge.get("a", ""))
            b = str(edge.get("b", ""))
            v = float(edge.get("value", 0.0))
            if not a or not b or a == b:
                continue
            raw[a] = raw.get(a, 0.0) + v * float(psi_prev.get(b, 0.0))
            raw[b] = raw.get(b, 0.0) + v * float(psi_prev.get(a, 0.0))

    evec = vectorize_evidence(evidence_t, concept_ids)
    for cid in concept_ids:
        raw[cid] += float(alpha) * float(evec.get(cid, 0.0))

    sat = {cid: saturate_signed(float(v), k=float(sat_k)) for cid, v in raw.items()}
    pruned = prune_small(sat, eps=float(prune_eps))
    return normalize_l1_abs(pruned), raw


def merge_propagated_with_evidence_off_index(
    propagated: Mapping[str, float],
    stabilized_pre_hex: Mapping[str, float],
    concept_index: list[str],
) -> dict[str, float]:
    """Replace in-index concepts with propagated state; keep stabilized values for concepts outside H_total index."""
    idx = set(concept_index)
    out: dict[str, float] = dict(stabilized_pre_hex)
    for cid in concept_index:
        out[cid] = float(propagated.get(cid, 0.0))
    return out


def update_semantic_state(
    psi_prev: Mapping[str, float] | None,
    evidence_t: Mapping[str, float],
    h_total: Mapping[str, Any],
    *,
    alpha: float = 0.7,
    sat_k: float = 1.2,
    prune_eps: float = 0.03,
) -> tuple[dict[str, float], dict[str, Any]]:
    """
    Full segment update plus per-segment audit payload (semantic_state block).
    """
    prev = dict(psi_prev or {})
    psi_next, raw = propagate_state(
        prev,
        evidence_t,
        h_total,
        alpha=alpha,
        sat_k=sat_k,
        prune_eps=prune_eps,
    )
    audit: dict[str, Any] = {
        "operator_applied": True,
        "alpha": float(alpha),
        "sat_k": float(sat_k),
        "prune_eps": float(prune_eps),
        "nonzero_concepts_before": _nonzero_count(raw),
        "nonzero_concepts_after": _nonzero_count(psi_next),
        "state_l1_abs": round(sum(abs(v) for v in psi_next.values()), 6),
        "top_concepts": _top_entries(psi_next, k=8),
    }
    return psi_next, audit


def build_semantic_dynamics_session_audit(
    h_total: Mapping[str, Any],
    *,
    path: str | None = None,
) -> dict[str, Any]:
    sym_ok, bnd_ok, detail = validate_h_total_symmetry_and_bounds(h_total)
    return {
        "h_total_loaded": True,
        "matrix_id": str(h_total.get("matrix_id") or ""),
        "version": str(h_total.get("version") or ""),
        "source_path": path,
        "concept_count": int(detail.get("concept_count") or 0),
        "edge_count": int(detail.get("edge_count") or 0),
        "symmetric_check_passed": bool(sym_ok),
        "bounded_check_passed": bool(bnd_ok),
    }
