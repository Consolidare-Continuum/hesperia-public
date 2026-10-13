# HESPERIA — CD Phase 1 executor (deterministic). Copyright © 2026 igareosh.com.
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from core.dynamics.numeric import quantize

from hesperia.engine.concept_dictionary.loader import load_cd_registry


def apply_saturation(score: float, k: float) -> float:
    """
    CD v1 saturation (documented in docs/governance/cd_v1/SATURATION_CLOSED_FORM.md).
    k in (0, 1]: compresses large scores; k >= 1.0 is identity on non-negative score.
    """
    s = max(0.0, float(score))
    kk = float(k)
    if kk >= 1.0:
        return quantize(s)
    denom = 1.0 + (1.0 - kk) * s
    return quantize(s / max(denom, 1e-12))


def _row_for(registry: dict[str, dict[str, Any]], cid: str) -> dict[str, Any]:
    return registry.get(cid) or registry["*"]


def _is_active(
    weight: float,
    evidence: int,
    row: dict[str, Any],
    *,
    min_evidence_global: int,
    confidence_floor_global: float,
) -> bool:
    act = row["activation"]
    thr = float(act.get("threshold", 0.0))
    val = row.get("validation") or {}
    min_e = int(val.get("min_evidence", min_evidence_global))
    floor = float(val.get("confidence_floor", confidence_floor_global))
    if evidence < min_e:
        return False
    if weight <= floor and weight <= thr:
        return False
    return weight > thr or evidence >= min_e


def apply_cd_phase1(
    concept_weights: dict[str, float],
    evidence_counts: dict[str, int],
    cd_jsonl: Path,
    *,
    cd_phase: int = 1,
    min_evidence_default: int = 1,
    confidence_floor_default: float = 0.0,
) -> dict[str, float]:
    """
    Phase 1: type+activation+requires/excludes+structure.primary_area (structure not cross-checked to B here).
    If cd_phase < 2, ignores co_occurs soft, effects, temporal / interaction.
    """
    if cd_phase < 1:
        return dict(sorted(concept_weights.items()))
    registry = load_cd_registry(cd_jsonl)
    weights = {k: float(concept_weights[k]) for k in sorted(concept_weights)}
    ev = {k: int(evidence_counts.get(k, 0)) for k in weights}

    # Step 2–3: per-concept validation + activation law
    out: dict[str, float] = {}
    for cid in sorted(weights):
        row = _row_for(registry, cid)
        w0 = float(weights[cid])
        e0 = int(ev.get(cid, 0))
        if not _is_active(
            w0,
            e0,
            row,
            min_evidence_global=min_evidence_default,
            confidence_floor_global=confidence_floor_default,
        ):
            continue
        act = row["activation"]
        base = float(act["base_weight"])
        cap = float(act["cap"])
        sat_k = float(act["saturation_k"])
        raw = base * float(e0)  # f(evidence) = count for Phase 1
        raw = min(raw, cap)
        raw = apply_saturation(raw, sat_k)
        out[cid] = quantize(raw)

    # requires (hard): drop cid if any required peer missing from active set
    for cid in list(out.keys()):
        row = _row_for(registry, cid)
        req = (row.get("constraints") or {}).get("requires") or []
        for other in req:
            if other not in out or out.get(other, 0.0) <= 0.0:
                out.pop(cid, None)
                break

    # excludes (hard): pairwise — drop lower weight; tie → drop lexicographically larger id
    to_remove: set[str] = set()
    for cid in sorted(out.keys()):
        row = _row_for(registry, cid)
        for other in (row.get("constraints") or {}).get("excludes") or []:
            if cid in to_remove or other not in out or cid not in out:
                continue
            vc, vo = float(out[cid]), float(out[other])
            if vc < vo:
                to_remove.add(cid)
            elif vc > vo:
                to_remove.add(other)
            else:
                to_remove.add(max(cid, other))
    for x in sorted(to_remove):
        out.pop(x, None)

    # Phase 2+: co_occurs soft (CO_OCCURS_MATH_PHASE2.md); before inhibit/amplify effects
    if cd_phase >= 2:
        alpha = 0.25
        beta = 0.15
        eps = 1e-9
        snap = dict(out)
        total_w = sum(snap.values())
        denom = eps + (total_w if total_w > 0 else eps)
        new_out: dict[str, float] = {}
        for cid in sorted(snap.keys()):
            row = _row_for(registry, cid)
            coco = (row.get("constraints") or {}).get("co_occurs") or []
            w0 = float(snap[cid])
            if not coco:
                new_out[cid] = quantize(w0)
                continue
            active_among = [o for o in coco if o in snap and float(snap[o]) > 0.0]
            miss = len(coco) - len(active_among)
            penalty = 1.0 / (1.0 + alpha * float(miss))
            s_co = sum(float(snap[o]) for o in active_among)
            boost = 1.0 + beta * min(1.0, s_co / denom)
            new_out[cid] = quantize(w0 * penalty * boost)
        out = new_out

    # Phase 2+: effects on targets (global inhibit pass, then global amplify pass)
    if cd_phase >= 2:
        for src in sorted(out.keys()):
            row = _row_for(registry, src)
            eff = row.get("effects") or {}
            for tgt, fac in sorted((eff.get("inhibits") or {}).items(), key=lambda x: x[0]):
                if tgt in out:
                    out[tgt] = quantize(float(out[tgt]) / max(float(fac), 1e-12))
        for src in sorted(out.keys()):
            row = _row_for(registry, src)
            eff = row.get("effects") or {}
            for tgt, fac in sorted((eff.get("amplifies") or {}).items(), key=lambda x: x[0]):
                if tgt in out:
                    out[tgt] = quantize(float(out[tgt]) * float(fac))

    return {k: quantize(v) for k, v in sorted(out.items())}


def default_cd_path(repo_root: Path) -> Path:
    return (
        repo_root
        / "assets"
        / "data"
        / "engine_dynamics_v060"
        / "concept_dict"
        / "concept_dict_cd.jsonl"
    )
