# HESPERIA — Topology dynamics from contradiction rows (deterministic).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import copy
import math
from types import SimpleNamespace
from typing import Any

from hesperia.extensions.triz.contradiction_coupling import _extract_pair_and_score, _row_pressure_score
from hesperia.extensions.triz.topology_binding import bind_contradiction_to_topology

_EPS = 1e-15


def _family_key_to_int(family_key: str) -> int:
    parts = str(family_key).split("_")
    if len(parts) >= 2 and parts[1].startswith("F"):
        try:
            return int(parts[1][1:])
        except ValueError:
            return -1
    return -1


def build_triz_concept_mapping(
    concept_to_area_family: dict[str, tuple[str, str]],
    area_ids: list[str],
) -> dict[str, Any]:
    """Map Dict-B (area string, family key) → matrix-style ids for ``bind_contradiction_to_topology``."""
    out: dict[str, Any] = {}
    for cid, (area_s, fam_k) in concept_to_area_family.items():
        try:
            ai = area_ids.index(str(area_s))
        except ValueError:
            ai = -1
        fi = _family_key_to_int(fam_k)
        out[str(cid)] = {"area_id": int(ai), "family_id": int(fi)}
    return out


def _sort_contradiction_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key_fn(idx_row: tuple[int, dict[str, Any]]) -> tuple[str, str, float, int]:
        idx, row = idx_row
        ca, cb, sc = _extract_pair_and_score(row)
        if ca is None or cb is None:
            return ("", "", 0.0, idx)
        a0, b0 = (ca, cb) if ca <= cb else (cb, ca)
        return (a0, b0, -sc, idx)

    ordered = sorted(enumerate(rows), key=key_fn)
    return [row for _, row in ordered]


def compute_segment_contradiction_loads(
    segment_results: list[dict[str, Any]],
    contradictions: list[dict[str, Any]] | None,
    concept_to_area_family: dict[str, tuple[str, str]],
    area_ids: list[str],
    *,
    topology_cal: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Per-segment contradiction mass from intersecting active concepts with contradiction pairs.
    Uses ``bind_contradiction_to_topology`` for cross-area / locality (no duplicated adjacency logic).
    """
    n = len(segment_results)
    if not contradictions:
        return [
            {
                "segment_index": i,
                "contradiction_load": 0.0,
                "area_contradiction_pressure": {a: 0.0 for a in area_ids},
                "contradiction_pairs_used": [],
                "cross_area_contradiction_mass": 0.0,
            }
            for i in range(n)
        ]

    triz_map = build_triz_concept_mapping(concept_to_area_family, area_ids)
    rows_sorted = _sort_contradiction_rows(list(contradictions))
    seg_inf = float((topology_cal or {}).get("segment_contradiction_influence", 1.0))
    summaries: list[dict[str, Any]] = []

    for seg_idx, seg in enumerate(segment_results):
        concepts = seg.get("concepts") or {}
        load = 0.0
        area_acc: dict[str, float] = {a: 0.0 for a in area_ids}
        cross_mass = 0.0
        pairs_used: list[dict[str, Any]] = []

        for row in rows_sorted:
            ca, cb, raw_sc = _extract_pair_and_score(row)
            w_sc = _row_pressure_score(row, use_effective=True)
            if ca is None or cb is None or w_sc <= _EPS:
                continue
            wa = concepts.get(ca)
            wb = concepts.get(cb)
            if wa is None or wb is None:
                continue
            try:
                fa = float(wa)
                fb = float(wb)
            except (TypeError, ValueError):
                continue
            if fa <= _EPS or fb <= _EPS:
                continue
            mass = float(w_sc) * min(fa, fb)
            load += mass

            af_a = concept_to_area_family.get(str(ca))
            af_b = concept_to_area_family.get(str(cb))
            if af_a and af_b:
                aa, ab = str(af_a[0]), str(af_b[0])
                if aa in area_acc and ab in area_acc:
                    if aa == ab:
                        area_acc[aa] += mass
                    else:
                        area_acc[aa] += mass
                        area_acc[ab] += mass
                        cross_mass += mass

            ns = SimpleNamespace(concept_a=str(ca), concept_b=str(cb))
            binding = bind_contradiction_to_topology(ns, triz_map)
            pairs_used.append(
                {
                    "pair": [str(ca), str(cb)],
                    "mass": round(mass, 6),
                    "raw_contradiction_score": float(raw_sc),
                    "effective_contradiction_score": round(float(w_sc), 6),
                    "same_area": bool(binding.get("same_area")),
                    "adjacent_areas": bool(binding.get("adjacent_areas")),
                    "locality_score": float(binding.get("locality_score") or 0.0),
                }
            )

        summaries.append(
            {
                "segment_index": seg_idx,
                "contradiction_load": float(load) * seg_inf,
                "area_contradiction_pressure": {a: float(v) * seg_inf for a, v in area_acc.items()},
                "contradiction_pairs_used": pairs_used,
                "cross_area_contradiction_mass": float(cross_mass) * seg_inf,
            }
        )

    max_load = max((s["contradiction_load"] for s in summaries), default=0.0)
    for s in summaries:
        raw_load = float(s["contradiction_load"])
        s["contradiction_load_normalized"] = (raw_load / max_load) if max_load > _EPS else 0.0
        ap = s["area_contradiction_pressure"]
        mx_ap = max(ap.values()) if ap else 0.0
        if mx_ap > _EPS:
            s["area_contradiction_pressure"] = {a: float(ap[a]) / mx_ap for a in area_ids}
        else:
            s["area_contradiction_pressure"] = {a: 0.0 for a in area_ids}

    return summaries


def apply_contradiction_to_segment_areas(
    segment_results: list[dict[str, Any]],
    contradiction_summaries: list[dict[str, Any]],
    area_ids: list[str],
    *,
    topology_cal: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """
    Destabilize dominance under contradiction load by mixing toward a uniform baseline.
    ``w`` is the normalized segment load (derived). Preserves total probability mass.
    """
    if not contradiction_summaries:
        return segment_results, False

    seg_inf = float((topology_cal or {}).get("segment_contradiction_influence", 1.0))
    out: list[dict[str, Any]] = []
    any_active = False
    for idx, row in enumerate(segment_results):
        s = row
        if idx < len(contradiction_summaries):
            summ = contradiction_summaries[idx]
            w = min(1.0, float(summ.get("contradiction_load_normalized") or 0.0) * seg_inf)
        else:
            summ = {}
            w = 0.0

        new_row = copy.deepcopy(row)
        areas = dict(new_row.get("areas") or {})
        pre = {a: float(areas.get(a, 0.0)) for a in area_ids}
        new_row["area_scores_pre_contradiction"] = pre

        if w <= _EPS:
            new_row["area_scores_post_contradiction"] = dict(pre)
            out.append(new_row)
            continue

        any_active = True
        u = 1.0 / float(len(area_ids))
        post = {}
        for a in area_ids:
            p = max(0.0, pre.get(a, 0.0))
            post[a] = (1.0 - w) * p + w * u
        tot = sum(post.values())
        if tot > _EPS:
            post = {a: post[a] / tot for a in area_ids}
        else:
            post = {a: u for a in area_ids}

        new_row["areas"] = post
        if "areas_final" in new_row:
            new_row["areas_final"] = post
        new_row["area_scores_post_contradiction"] = post
        new_row["contradiction_load"] = float(summ.get("contradiction_load") or 0.0)
        new_row["contradiction_load_normalized"] = w
        new_row["cross_area_contradiction_mass"] = float(summ.get("cross_area_contradiction_mass") or 0.0)
        new_row["area_contradiction_pressure"] = dict(summ.get("area_contradiction_pressure") or {})
        new_row["contradiction_pairs_used"] = list(summ.get("contradiction_pairs_used") or [])
        out.append(new_row)

    return out, any_active


def compute_transition_pressure(
    contradiction_summaries: list[dict[str, Any]],
    area_ids: list[str],
    *,
    topology_cal: dict[str, Any] | None = None,
) -> list[float]:
    """Between consecutive segments: L1 distance of normalized area contradiction pressure + load delta."""
    if len(contradiction_summaries) < 2:
        return []

    tp_inf = float((topology_cal or {}).get("transition_pressure_influence", 1.0))
    pressures: list[list[float]] = []
    loads: list[float] = []
    for s in contradiction_summaries:
        ap = s.get("area_contradiction_pressure") or {}
        pressures.append([float(ap.get(a, 0.0)) for a in area_ids])
        loads.append(float(s.get("contradiction_load_normalized") or 0.0))

    out: list[float] = []
    for i in range(len(pressures) - 1):
        d_area = sum(abs(pressures[i][j] - pressures[i + 1][j]) for j in range(len(area_ids)))
        d_load = abs(loads[i + 1] - loads[i])
        val = (d_area + d_load) * tp_inf
        out.append(float(val))

    mx = max(out) if out else 0.0
    if mx <= _EPS:
        return [0.0 for _ in out]
    normed = [float(v) / mx for v in out]
    # Apply responsiveness after normalization so calibration does not cancel uniformly under max-norm.
    return [min(1.0, float(x) * tp_inf) for x in normed]


def segment_momentum_factors_from_loads(
    contradiction_summaries: list[dict[str, Any]],
    *,
    topology_cal: dict[str, Any] | None = None,
) -> list[float]:
    """Higher contradiction load → lower momentum carry (derived, no hand-tuned area table)."""
    mom_inf = float((topology_cal or {}).get("momentum_attenuation_influence", 1.0))
    out: list[float] = []
    for s in contradiction_summaries:
        ln = float(s.get("contradiction_load_normalized") or 0.0)
        out.append(max(0.0, min(1.0, 1.0 - ln * mom_inf)))
    return out


def build_contradiction_coupling_summary(
    contradiction_summaries: list[dict[str, Any]],
    transition_pressure: list[float],
    coupling_active: bool,
) -> dict[str, Any]:
    loads = [float(s.get("contradiction_load_normalized") or 0.0) for s in contradiction_summaries]
    with_conflict = sum(1 for x in loads if x > _EPS)
    max_load = max(loads) if loads else 0.0
    mean_tp = sum(transition_pressure) / len(transition_pressure) if transition_pressure else 0.0
    return {
        "segment_count_with_conflict": int(with_conflict),
        "max_segment_contradiction_load": round(max_load, 6),
        "mean_transition_pressure": round(mean_tp, 6),
        "contradiction_coupling_active": bool(coupling_active),
    }
