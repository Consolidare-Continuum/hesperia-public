# HESPERIA — Contradiction coupling for TFP area activation (deterministic).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import math
from typing import Any

from core.math.signal_normalization import sublinear_compress as _smooth_pressure_accum
from hesperia.extensions.triz.contradiction_negation import (
    build_negation_activation_summary,
    classify_contradiction_mode,
    pair_effective_activation_latent,
)

_EPS = 1e-15
CONTRADICTION_COUPLING_VERSION = "contradiction_coupling_task6"


def _extract_pair_and_score(row: dict[str, Any]) -> tuple[str | None, str | None, float]:
    """Parse contradiction row: ``pair`` or ``concept_a``/``concept_b``; score keys in fixed order."""
    ca: str | None = None
    cb: str | None = None
    raw_pair = row.get("pair")
    if isinstance(raw_pair, (list, tuple)) and len(raw_pair) >= 2:
        ca = str(raw_pair[0]) if raw_pair[0] is not None else None
        cb = str(raw_pair[1]) if raw_pair[1] is not None else None
    else:
        if row.get("concept_a") is not None:
            ca = str(row["concept_a"])
        if row.get("concept_b") is not None:
            cb = str(row["concept_b"])
    score = 0.0
    if "raw_contradiction_score" in row and row["raw_contradiction_score"] is not None:
        score = float(row["raw_contradiction_score"])
    elif "score" in row and row["score"] is not None:
        score = float(row["score"])
    if not math.isfinite(score):
        score = 0.0
    return ca, cb, score


def _sort_contradiction_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable deterministic ordering before accumulation."""

    def key_fn(idx_row: tuple[int, dict[str, Any]]) -> tuple[str, str, float, int]:
        idx, row = idx_row
        ca, cb, sc = _extract_pair_and_score(row)
        if ca is None or cb is None:
            return ("", "", 0.0, idx)
        a0, b0 = (ca, cb) if ca <= cb else (cb, ca)
        return (a0, b0, -sc, idx)

    enumerated = list(enumerate(rows))
    enumerated.sort(key=key_fn)
    return [row for _, row in enumerated]


def _resolve_area(concept_id: str, concept_to_area_family: dict[str, tuple[str, str]]) -> str | None:
    af = concept_to_area_family.get(concept_id)
    if not af:
        return None
    return str(af[0])


def count_contradiction_rows_used(
    contradictions: list[dict[str, Any]] | None,
    concept_to_area_family: dict[str, tuple[str, str]],
    area_ids: list[str],
) -> int:
    """Rows with positive score and both concepts resolving to known areas."""
    if not contradictions:
        return 0
    valid_areas = set(area_ids)
    n = 0
    for row in _sort_contradiction_rows(list(contradictions)):
        ca, cb, sc = _extract_pair_and_score(row)
        if ca is None or cb is None or sc <= _EPS:
            continue
        aa = _resolve_area(ca, concept_to_area_family)
        ab = _resolve_area(cb, concept_to_area_family)
        if aa is None or ab is None:
            continue
        if aa not in valid_areas or ab not in valid_areas:
            continue
        n += 1
    return n


def concept_support_strength(concept_id: str, concept_weights: dict[str, float]) -> float:
    """Relative support for a concept in current activation mass (deterministic)."""
    if not concept_weights:
        return 0.2
    mx = max(float(v) for v in concept_weights.values())
    if mx <= _EPS:
        return 0.2
    w = float(concept_weights.get(str(concept_id), 0.0))
    return max(0.12, min(1.0, w / mx))


def pair_confidence(
    ca: str,
    cb: str,
    uncertainty_package: dict[str, Any] | None,
    concept_weights: dict[str, float] | None,
    *,
    uncertainty_cal: dict[str, Any] | None = None,
) -> float:
    """Trust in a contradiction pair given lexical/concept uncertainty (not suppression by keyword)."""
    uc = uncertainty_cal or {}
    sens = float(uc.get("confidence_sensitivity", 1.0))
    floor = max(0.0, float(uc.get("confidence_floor", 0.0)))
    fuzz_inf = float(uc.get("fuzzy_penalty_influence", 1.0))
    amb_inf = float(uc.get("ambiguity_penalty_influence", 1.0))

    if uncertainty_package is None:
        return max(floor, min(1.0, 1.0))
    lex_u = float(uncertainty_package.get("lexical_uncertainty") or 0.0)
    con_u = float(uncertainty_package.get("concept_uncertainty") or 0.0)
    base = max(0.1, min(1.0, 1.0 - sens * (0.46 * lex_u + 0.46 * con_u)))
    fuzzy = float(uncertainty_package.get("fuzzy_link_ratio") or 0.0)
    amb = float(uncertainty_package.get("ambiguous_concept_share") or 0.0)
    base = max(0.06, base * max(0.05, 1.0 - 0.22 * fuzz_inf * fuzzy - 0.18 * amb_inf * amb))
    cw = concept_weights or {}
    sa = concept_support_strength(ca, cw)
    sb = concept_support_strength(cb, cw)
    geom = math.sqrt(max(_EPS, sa) * max(_EPS, sb))
    return max(floor, max(0.06, min(1.0, base * geom)))


def enrich_contradiction_rows(
    rows: list[dict[str, Any]] | None,
    uncertainty_package: dict[str, Any] | None,
    concept_weights: dict[str, float] | None,
    *,
    concept_weights_stabilized: dict[str, float] | None = None,
    hex_feedback_delta: dict[str, float] | None = None,
    lexical_negation_summary: dict[str, Any] | None = None,
    concept_to_area_family: dict[str, tuple[str, str]] | None = None,
    contradiction_calibration: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Attach ``confidence``, ``effective_score`` (activation-side), mode, and dual effective scores.

    When stabilization / hex summaries are omitted, behavior matches task5 (mode ambiguous, scores equal).
    """
    if not rows:
        return []
    cal = contradiction_calibration or {}
    unc_cal = dict(cal.get("uncertainty") or {})
    neg_cal = dict(cal.get("negation_inhibition") or {})
    cw = concept_weights or {}
    stab = concept_weights_stabilized if concept_weights_stabilized is not None else cw
    hd = hex_feedback_delta if isinstance(hex_feedback_delta, dict) else {}
    neg_b: dict[str, float] = {}
    inh_b: dict[str, float] = {}
    if stab and cw:
        nas = build_negation_activation_summary(stab, cw, hd, lexical_negation_summary)
        neg_b = {str(k): float(v) for k, v in (nas.get("concept_negation_burden") or {}).items()}
        for cid in set(stab) | set(cw):
            s = max(0.0, float(stab.get(str(cid), 0.0) or 0.0))
            p = max(0.0, float(cw.get(str(cid), 0.0) or 0.0))
            if s <= _EPS:
                inh_b[str(cid)] = 0.0
            else:
                inh_b[str(cid)] = max(0.0, min(1.0, 1.0 - p / s))

    out: list[dict[str, Any]] = []
    for row in _sort_contradiction_rows(list(rows)):
        r = dict(row)
        ca, cb, raw_score = _extract_pair_and_score(r)
        r["raw_contradiction_score"] = float(raw_score)
        if concept_to_area_family:
            afa = concept_to_area_family.get(str(ca or ""))
            afb = concept_to_area_family.get(str(cb or ""))
            family_a = str(afa[1]) if afa else ""
            family_b = str(afb[1]) if afb else ""
            r["family_a"] = family_a
            r["family_b"] = family_b
            r["same_family_conflict"] = bool(family_a and family_b and family_a == family_b)
            r["cross_family_conflict"] = bool(family_a and family_b and family_a != family_b)
        if ca is None or cb is None or raw_score <= _EPS:
            r["confidence"] = 0.0
            r["effective_score"] = 0.0
            r["mode"] = "ambiguous_opposition"
            r["effective_activation_score"] = 0.0
            r["effective_latent_conflict_score"] = 0.0
            r["negation_factor"] = 0.0
            r["inhibition_factor"] = 0.0
            r["coactivation_factor"] = 0.0
            out.append(r)
            continue
        conf = pair_confidence(str(ca), str(cb), uncertainty_package, cw, uncertainty_cal=unc_cal)
        r["confidence"] = round(conf, 6)
        if not neg_b and not inh_b:
            eff = float(raw_score) * conf
            r["effective_score"] = round(eff, 6)
            r["mode"] = "ambiguous_opposition"
            r["effective_activation_score"] = round(eff, 6)
            r["effective_latent_conflict_score"] = round(eff, 6)
            r["negation_factor"] = 0.0
            r["inhibition_factor"] = 0.0
            r["coactivation_factor"] = 0.0
            out.append(r)
            continue

        cls = classify_contradiction_mode(
            concept_a=str(ca),
            concept_b=str(cb),
            raw_scores={str(k): float(v) for k, v in stab.items()},
            post_hex_scores={str(k): float(v) for k, v in cw.items()},
            concept_negation_burden=neg_b,
            concept_inhibition_burden=inh_b,
        )
        mode = str(cls.get("mode") or "ambiguous_opposition")
        r["mode"] = mode
        r["negation_factor"] = float(cls.get("negation_factor") or 0.0)
        r["inhibition_factor"] = float(cls.get("inhibition_factor") or 0.0)
        r["coactivation_factor"] = float(cls.get("coactivation_factor") or 0.0)

        eff_act, eff_lat = pair_effective_activation_latent(
            mode,
            float(raw_score),
            float(conf),
            float(r["negation_factor"]),
            float(r["inhibition_factor"]),
            float(r["coactivation_factor"]),
            mode_weights=neg_cal,
        )
        r["effective_activation_score"] = round(eff_act, 6)
        r["effective_latent_conflict_score"] = round(eff_lat, 6)
        r["effective_score"] = round(eff_act, 6)
        out.append(r)
    return out


def _row_pressure_score(
    row: dict[str, Any],
    *,
    use_effective: bool,
    score_field: str = "effective_activation_score",
) -> float:
    if use_effective:
        if row.get(score_field) is not None:
            return float(row[score_field])
        if row.get("effective_score") is not None:
            return float(row["effective_score"])
    if row.get("raw_contradiction_score") is not None:
        return float(row["raw_contradiction_score"])
    _, _, sc = _extract_pair_and_score(row)
    return float(sc)


def build_area_contradiction_pressure(
    contradictions: list[dict[str, Any]] | None,
    concept_to_area_family: dict[str, tuple[str, str]],
    area_ids: list[str],
    *,
    use_effective_scores: bool = True,
    use_latent_scores: bool = False,
    activation_cal: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Per-area pressure in [0, 1], max- or sum-normalized. Activation field unless ``use_latent_scores``."""
    accum = {a: 0.0 for a in area_ids}
    valid_areas = set(area_ids)
    if not contradictions:
        return accum

    ac = activation_cal or {}
    smooth = float(ac.get("pressure_smooth_compression", 1.0))
    norm_mode = str(ac.get("pressure_normalization_mode") or "max")
    area_inf = float(ac.get("area_contradiction_influence", 1.0))

    field = "effective_latent_conflict_score" if use_latent_scores else "effective_activation_score"
    for row in _sort_contradiction_rows(list(contradictions)):
        ca, cb, _s = _extract_pair_and_score(row)
        sc = _row_pressure_score(row, use_effective=use_effective_scores, score_field=field)
        if ca is None or cb is None or sc <= _EPS:
            continue
        aa = _resolve_area(ca, concept_to_area_family)
        ab = _resolve_area(cb, concept_to_area_family)
        if aa is None or ab is None or aa not in valid_areas or ab not in valid_areas:
            continue
        accum[aa] += sc
        if aa != ab:
            accum[ab] += sc

    for a in area_ids:
        accum[a] = _smooth_pressure_accum(accum[a], smooth)

    if norm_mode == "sum":
        s = sum(accum.values())
        if s <= _EPS:
            return {a: 0.0 for a in area_ids}
        out = {a: float(accum[a]) / s for a in area_ids}
    else:
        max_p = max(accum.values()) if accum else 0.0
        if max_p <= _EPS:
            return {a: 0.0 for a in area_ids}
        out = {a: float(accum[a]) / max_p for a in area_ids}

    if abs(area_inf - 1.0) > _EPS:
        out = {a: min(1.0, float(out[a]) * area_inf) for a in area_ids}
        mx2 = max(out.values()) if out else 0.0
        if mx2 > _EPS:
            out = {a: float(out[a]) / mx2 for a in area_ids}
        else:
            out = {a: 0.0 for a in area_ids}
    return out


def build_dynamic_inhibition_delta(
    contradictions: list[dict[str, Any]] | None,
    concept_to_area_family: dict[str, tuple[str, str]],
    area_ids: list[str],
    *,
    use_effective_scores: bool = True,
    use_latent_scores: bool = True,
    activation_cal: dict[str, Any] | None = None,
) -> list[list[float]]:
    """Symmetric off-diagonal inhibition delta; prefers latent effective scores for suppressed conflict."""
    n = len(area_ids)
    delta = [[0.0 for _ in range(n)] for _ in range(n)]
    index = {aid: i for i, aid in enumerate(area_ids)}
    valid_areas = set(area_ids)
    dyn_inf = float((activation_cal or {}).get("dynamic_inhibition_influence", 1.0))

    if not contradictions:
        return delta

    field = "effective_latent_conflict_score" if use_latent_scores else "effective_activation_score"
    for row in _sort_contradiction_rows(list(contradictions)):
        ca, cb, _s = _extract_pair_and_score(row)
        sc = _row_pressure_score(row, use_effective=use_effective_scores, score_field=field)
        if ca is None or cb is None or sc <= _EPS:
            continue
        aa = _resolve_area(ca, concept_to_area_family)
        ab = _resolve_area(cb, concept_to_area_family)
        if aa is None or ab is None or aa not in valid_areas or ab not in valid_areas:
            continue
        i, j = index[aa], index[ab]
        if i == j:
            continue
        delta[i][j] += sc * dyn_inf
        delta[j][i] += sc * dyn_inf

    max_cell = max(delta[i][j] for i in range(n) for j in range(n))
    if max_cell <= _EPS:
        return delta
    inv = 1.0 / max_cell
    return [[delta[i][j] * inv for j in range(n)] for i in range(n)]


def _apply_area_inhibition_matrix(
    area_raw: dict[str, float],
    *,
    matrix: list[list[float]],
    area_ids: list[str],
    inhibition_scale: float,
) -> dict[str, float]:
    vector = [max(0.0, float(area_raw.get(area_id, 0.0))) for area_id in area_ids]
    scale = max(0.0, float(inhibition_scale))
    inhibited: dict[str, float] = {}
    n = len(area_ids)
    for i, area_id in enumerate(area_ids):
        inhibition = 0.0
        for j in range(n):
            inhibition += float(matrix[i][j]) * vector[j]
        inhibited[area_id] = max(0.0, vector[i] - inhibition * scale)
    return inhibited


def apply_contradiction_coupling(
    areas_raw: dict[str, float],
    base_matrix: list[list[float]],
    contradiction_pressure: dict[str, float],
    dynamic_delta: list[list[float]],
    area_ids: list[str],
    *,
    inhibition_scale: float = 1.0,
) -> dict[str, Any]:
    """
    Apply pressure attenuation, combine inhibition matrices, run inhibition pass.

    When combined matrix max exceeds 1.0, scale all entries down uniformly (diagonal stays zero).
    """
    n = len(area_ids)
    # Pressure-adjusted raw areas
    areas_pressure_adjusted: dict[str, float] = {}
    for aid in area_ids:
        raw_v = max(0.0, float(areas_raw.get(aid, 0.0)))
        p = min(1.0, max(0.0, float(contradiction_pressure.get(aid, 0.0))))
        areas_pressure_adjusted[aid] = max(0.0, raw_v * (1.0 - p))

    base: list[list[float]] = []
    for i in range(n):
        row = list(base_matrix[i]) if i < len(base_matrix) else []
        if len(row) < n:
            row = row + [0.0] * (n - len(row))
        base.append([float(row[j]) for j in range(n)])

    dlt: list[list[float]] = []
    for i in range(n):
        row = list(dynamic_delta[i]) if i < len(dynamic_delta) else []
        if len(row) < n:
            row = row + [0.0] * (n - len(row))
        dlt.append([float(row[j]) for j in range(n)])

    dynamic: list[list[float]] = []
    for i in range(n):
        dynamic.append([base[i][j] + dlt[i][j] for j in range(n)])
        dynamic[i][i] = 0.0

    mx = max(dynamic[i][j] for i in range(n) for j in range(n))
    if mx > 1.0 + _EPS:
        inv = 1.0 / mx
        dynamic = [[dynamic[i][j] * inv for j in range(n)] for i in range(n)]
        for i in range(n):
            dynamic[i][i] = 0.0

    areas_inhibited = _apply_area_inhibition_matrix(
        areas_pressure_adjusted,
        matrix=dynamic,
        area_ids=area_ids,
        inhibition_scale=inhibition_scale,
    )

    return {
        "areas_pressure_adjusted": areas_pressure_adjusted,
        "inhibition_matrix_dynamic": dynamic,
        "areas_inhibited": areas_inhibited,
        "contradiction_pressure": dict(contradiction_pressure),
        "dynamic_inhibition_delta": dlt,
    }
