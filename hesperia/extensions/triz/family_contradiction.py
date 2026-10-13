from __future__ import annotations

import math
from typing import Any

from core.math.basic_stats import clamp01 as _clamp01

_EPS = 1e-15


def _row_score(row: dict[str, Any], *, use_effective: bool) -> float:
    if use_effective:
        for key in ("effective_activation_score", "effective_score"):
            if row.get(key) is not None:
                return float(row.get(key) or 0.0)
    if row.get("raw_contradiction_score") is not None:
        return float(row.get("raw_contradiction_score") or 0.0)
    if row.get("score") is not None:
        return float(row.get("score") or 0.0)
    return 0.0


def _resolve_family(concept_id: str, concept_to_area_family: dict[str, tuple[str, str]]) -> tuple[str | None, str | None]:
    af = concept_to_area_family.get(str(concept_id))
    if not af:
        return None, None
    area = str(af[0])
    family = str(af[1])
    return area, f"{area}_{family}"


def build_family_contradiction_pressure(
    contradiction_rows: list[dict[str, Any]] | None,
    concept_to_area_family: dict[str, tuple[str, str]],
) -> dict[str, dict[str, float]]:
    raw: dict[str, float] = {}
    eff: dict[str, float] = {}
    if not contradiction_rows:
        return {"raw": {}, "effective": {}}
    for row in contradiction_rows:
        pair = row.get("pair")
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        _, fa = _resolve_family(str(pair[0]), concept_to_area_family)
        _, fb = _resolve_family(str(pair[1]), concept_to_area_family)
        if not fa or not fb:
            continue
        r = _row_score(row, use_effective=False)
        e = _row_score(row, use_effective=True)
        if r > _EPS:
            raw[fa] = raw.get(fa, 0.0) + r
            raw[fb] = raw.get(fb, 0.0) + r
        if e > _EPS:
            eff[fa] = eff.get(fa, 0.0) + e
            eff[fb] = eff.get(fb, 0.0) + e

    def _norm(d: dict[str, float]) -> dict[str, float]:
        if not d:
            return {}
        m = max(d.values())
        if m <= _EPS:
            return {k: 0.0 for k in sorted(d)}
        return {k: round(float(d[k]) / m, 6) for k in sorted(d)}

    return {"raw": _norm(raw), "effective": _norm(eff)}


def build_family_contradiction_matrix(
    contradiction_rows: list[dict[str, Any]] | None,
    concept_to_area_family: dict[str, tuple[str, str]],
) -> dict[str, dict[str, float]]:
    mat: dict[str, dict[str, float]] = {}
    if not contradiction_rows:
        return {}
    for row in contradiction_rows:
        pair = row.get("pair")
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        _, fa = _resolve_family(str(pair[0]), concept_to_area_family)
        _, fb = _resolve_family(str(pair[1]), concept_to_area_family)
        if not fa or not fb:
            continue
        sc = _row_score(row, use_effective=True)
        if sc <= _EPS:
            continue
        if fa not in mat:
            mat[fa] = {}
        if fb not in mat:
            mat[fb] = {}
        mat[fa][fb] = mat[fa].get(fb, 0.0) + sc
        if fa != fb:
            mat[fb][fa] = mat[fb].get(fa, 0.0) + sc
    return {fa: {fb: round(v, 6) for fb, v in sorted(row.items())} for fa, row in sorted(mat.items())}


def compute_family_fragmentation(
    family_pressure_effective: dict[str, float],
    family_activation: dict[str, float],
    family_to_area: dict[str, str],
) -> dict[str, Any]:
    area_family_fragmentation: dict[str, float] = {}
    by_area: dict[str, list[tuple[str, float, float]]] = {}
    for fam, act in family_activation.items():
        area = family_to_area.get(str(fam))
        if not area:
            continue
        by_area.setdefault(area, []).append(
            (
                str(fam),
                max(0.0, float(act)),
                max(0.0, float(family_pressure_effective.get(str(fam), 0.0))),
            )
        )
    for area, rows in by_area.items():
        tot_act = sum(x[1] for x in rows)
        if tot_act <= _EPS:
            area_family_fragmentation[area] = 0.0
            continue
        weighted = sum((x[2] * x[1]) for x in rows) / tot_act
        area_family_fragmentation[area] = round(_clamp01(weighted), 6)
    global_frag = _clamp01(sum(area_family_fragmentation.values()) / max(1, len(area_family_fragmentation)))
    dom = sorted(family_pressure_effective.items(), key=lambda kv: (-float(kv[1]), kv[0]))[:5]
    return {
        "area_family_fragmentation": {k: area_family_fragmentation[k] for k in sorted(area_family_fragmentation)},
        "global_family_fragmentation": round(global_frag, 6),
        "dominant_conflict_families": [str(k) for k, _ in dom],
    }


def compute_family_bridge_conflict(
    family_contradiction_matrix: dict[str, dict[str, float]],
    family_to_area: dict[str, str],
) -> dict[str, float]:
    cross = 0.0
    intra = 0.0
    seen: set[tuple[str, str]] = set()
    for fa, row in family_contradiction_matrix.items():
        aa = family_to_area.get(str(fa))
        for fb, val in row.items():
            key = (fa, fb) if fa <= fb else (fb, fa)
            if key in seen:
                continue
            seen.add(key)
            ab = family_to_area.get(str(fb))
            v = max(0.0, float(val))
            if not aa or not ab:
                continue
            if aa == ab:
                intra += v
            else:
                cross += v
    denom = cross + intra
    if denom <= _EPS:
        return {
            "family_cross_area_bridge_mass": 0.0,
            "family_intra_area_conflict_mass": 0.0,
        }
    return {
        "family_cross_area_bridge_mass": round(_clamp01(cross / denom), 6),
        "family_intra_area_conflict_mass": round(_clamp01(intra / denom), 6),
    }


def family_conflict_concentration(family_pressure_effective: dict[str, float]) -> float:
    vals = [max(0.0, float(v)) for v in family_pressure_effective.values()]
    if not vals:
        return 0.0
    s = sum(vals)
    if s <= _EPS:
        return 0.0
    vals = sorted((v / s for v in vals), reverse=True)
    top = vals[: min(3, len(vals))]
    return round(_clamp01(sum(top)), 6)
