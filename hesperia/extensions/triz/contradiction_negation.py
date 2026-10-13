# HESPERIA — Contradiction × negation × inhibition modes (v0.5.8 task6).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import math
from typing import Any, Literal

from core.math.basic_stats import clamp01 as _clamp01

_EPS = 1e-15
CONTRADICTION_NEGATION_VERSION = "contradiction_negation_task6"

OppositionMode = Literal[
    "coactive_opposition",
    "negated_opposition",
    "inhibited_opposition",
    "ambiguous_opposition",
]


def build_negation_activation_summary(
    stabilized_pre_hex: dict[str, float],
    concepts_post_hex: dict[str, float],
    hex_feedback_delta: dict[str, float],
    lexical_negation_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Concept-level negation burden + share, combining lexical negation mass proxy with hex pullback.
    """
    lex = lexical_negation_summary or {}
    n_global = _clamp01(float(lex.get("negated_marker_ratio") or 0.0))
    n_concept_lex = _clamp01(float(lex.get("negated_concept_ratio") or 0.0))
    total_stab = sum(max(0.0, float(v)) for v in stabilized_pre_hex.values()) or 1.0

    neg_burden: dict[str, float] = {}
    for cid in sorted(set(stabilized_pre_hex) | set(concepts_post_hex)):
        stab = max(0.0, float(stabilized_pre_hex.get(cid, 0.0) or 0.0))
        post = max(0.0, float(concepts_post_hex.get(cid, 0.0) or 0.0))
        hd = float(hex_feedback_delta.get(cid, 0.0) or 0.0)
        mass_share = stab / total_stab if total_stab > _EPS else 0.0
        lexical_term = _clamp01(0.55 * n_global * mass_share + 0.45 * n_concept_lex * mass_share)
        hex_pull = 0.0
        if stab > _EPS and hd < 0.0:
            hex_pull = _clamp01(min(1.0, abs(hd) / (stab + _EPS)))
        neg_burden[cid] = _clamp01(max(lexical_term, hex_pull * 0.62 + lexical_term * 0.38))

    negated_concept_share = (
        sum(neg_burden.values()) / float(len(neg_burden)) if neg_burden else 0.0
    )
    return {
        "negation_trace_version": CONTRADICTION_NEGATION_VERSION,
        "concept_negation_burden": {k: round(v, 6) for k, v in sorted(neg_burden.items())},
        "negated_concept_share": round(_clamp01(negated_concept_share), 6),
    }


def build_concept_inhibition_summary(
    stabilized_pre_hex: dict[str, float],
    concepts_post_hex: dict[str, float],
    hex_feedback_delta: dict[str, float],
    concept_to_area_family: dict[str, tuple[str, str]],
    area_ids: list[str],
) -> dict[str, Any]:
    """Per-concept inhibition vs area-aggregated inhibition burden (deterministic)."""
    delta: dict[str, float] = {}
    inh_burden: dict[str, float] = {}
    for cid in sorted(set(stabilized_pre_hex) | set(concepts_post_hex)):
        stab = max(0.0, float(stabilized_pre_hex.get(cid, 0.0) or 0.0))
        post = max(0.0, float(concepts_post_hex.get(cid, 0.0) or 0.0))
        delta[cid] = round(post - stab, 6)
        if stab <= _EPS:
            inh_burden[cid] = 0.0
        else:
            inh_burden[cid] = _clamp01(1.0 - post / stab)

    area_mass: dict[str, float] = {a: 0.0 for a in area_ids}
    area_inh_num: dict[str, float] = {a: 0.0 for a in area_ids}
    for cid, w in stabilized_pre_hex.items():
        af = concept_to_area_family.get(str(cid))
        if not af:
            continue
        area_id = str(af[0])
        if area_id not in area_mass:
            continue
        m = max(0.0, float(w))
        area_mass[area_id] += m
        area_inh_num[area_id] += m * float(inh_burden.get(str(cid), 0.0))

    area_inhibition_burden: dict[str, float] = {}
    for aid in area_ids:
        m = area_mass.get(aid, 0.0)
        if m <= _EPS:
            area_inhibition_burden[aid] = 0.0
        else:
            area_inhibition_burden[aid] = round(area_inh_num.get(aid, 0.0) / m, 6)

    return {
        "negation_trace_version": CONTRADICTION_NEGATION_VERSION,
        "concept_raw_vs_post_hex_delta": {k: delta[k] for k in sorted(delta)},
        "concept_inhibition_burden": {k: round(inh_burden[k], 6) for k in sorted(inh_burden)},
        "area_inhibition_burden": {k: area_inhibition_burden[k] for k in sorted(area_inhibition_burden)},
        "hex_feedback_delta_echo": {k: round(float(hex_feedback_delta.get(k, 0.0) or 0.0), 6) for k in sorted(hex_feedback_delta)},
    }


def classify_contradiction_mode(
    *,
    concept_a: str,
    concept_b: str,
    raw_scores: dict[str, float],
    post_hex_scores: dict[str, float],
    concept_negation_burden: dict[str, float],
    concept_inhibition_burden: dict[str, float],
) -> dict[str, Any]:
    """
    Structural opposition mode for one contradiction pair (machine fields, not prose).
    raw_scores = stabilized pre-hex masses; post_hex_scores = post-hex masses.
    """
    na = _clamp01(float(concept_negation_burden.get(str(concept_a), 0.0)))
    nb = _clamp01(float(concept_negation_burden.get(str(concept_b), 0.0)))
    ia = _clamp01(float(concept_inhibition_burden.get(str(concept_a), 0.0)))
    ib = _clamp01(float(concept_inhibition_burden.get(str(concept_b), 0.0)))
    neg_max = max(na, nb)
    inh_max = max(ia, ib)

    pa = max(0.0, float(post_hex_scores.get(str(concept_a), 0.0) or 0.0))
    pb = max(0.0, float(post_hex_scores.get(str(concept_b), 0.0) or 0.0))
    ra = max(0.0, float(raw_scores.get(str(concept_a), 0.0) or 0.0))
    rb = max(0.0, float(raw_scores.get(str(concept_b), 0.0) or 0.0))

    denom = max(max(pa, pb), _EPS)
    coactivation_factor = _clamp01(min(pa, pb) / denom)

    if neg_max >= 0.34 and neg_max + 0.02 >= inh_max:
        mode: OppositionMode = "negated_opposition"
    elif inh_max >= 0.36 and inh_max > neg_max + 0.04:
        mode = "inhibited_opposition"
    elif coactivation_factor >= 0.30 and neg_max < 0.30 and inh_max < 0.33:
        mode = "coactive_opposition"
    else:
        mode = "ambiguous_opposition"

    return {
        "mode": mode,
        "negation_factor": round(neg_max, 6),
        "inhibition_factor": round(inh_max, 6),
        "coactivation_factor": round(coactivation_factor, 6),
        "support_raw_a": round(ra, 6),
        "support_raw_b": round(rb, 6),
        "support_post_a": round(pa, 6),
        "support_post_b": round(pb, 6),
    }


def pair_effective_activation_latent(
    mode: str,
    raw_score: float,
    confidence: float,
    negation_factor: float,
    inhibition_factor: float,
    coactivation_factor: float,
    *,
    mode_weights: dict[str, float] | None = None,
) -> tuple[float, float]:
    """Split overt activation conflict vs latent / suppressed conflict."""
    mw = mode_weights or {}
    w_neg_act = float(mw.get("negated_opposition_activation_weight", 1.0))
    w_inh_act = float(mw.get("inhibited_opposition_activation_weight", 1.0))
    w_inh_lat = float(mw.get("inhibited_opposition_latent_weight", 1.0))
    w_co_lat = float(mw.get("coactive_opposition_latent_weight", 1.0))

    base = max(0.0, float(raw_score)) * max(0.0, float(confidence))
    nf = _clamp01(float(negation_factor))
    inf = _clamp01(float(inhibition_factor))
    cf = _clamp01(float(coactivation_factor))

    if mode == "coactive_opposition":
        eff_act = base
        eff_lat = base * _clamp01(0.86 + 0.14 * cf) * w_co_lat
        return eff_act, eff_lat
    if mode == "negated_opposition":
        eff_act = base * _clamp01(0.62 + 0.28 * (1.0 - nf)) * w_neg_act
        eff_lat = base * _clamp01(0.78 + 0.22 * nf)
        return eff_act, eff_lat
    if mode == "inhibited_opposition":
        eff_act = base * max(0.05, 1.0 - 0.58 * inf) * w_inh_act
        eff_lat = base * _clamp01(0.45 + 0.55 * inf) * w_inh_lat
        return eff_act, eff_lat
    eff = base * _clamp01(0.72 + 0.14 * max(0.0, float(confidence)))
    return eff, eff


def build_contradiction_mode_summary(enriched_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate share of each opposition mode over processed contradiction rows."""
    keys = (
        "coactive_opposition",
        "negated_opposition",
        "inhibited_opposition",
        "ambiguous_opposition",
    )
    counts = {k: 0 for k in keys}
    for r in enriched_rows:
        if not isinstance(r, dict):
            continue
        m = str(r.get("mode") or "ambiguous_opposition")
        if m not in counts:
            m = "ambiguous_opposition"
        counts[m] += 1
    total = sum(counts.values()) or 1
    out: dict[str, Any] = {
        "coactive_opposition_share": round(counts["coactive_opposition"] / total, 6),
        "negated_opposition_share": round(counts["negated_opposition"] / total, 6),
        "inhibited_opposition_share": round(counts["inhibited_opposition"] / total, 6),
        "ambiguous_opposition_share": round(counts["ambiguous_opposition"] / total, 6),
    }
    return out


def crossplane_negation_inhibition_components(
    enriched_rows: list[dict[str, Any]],
) -> tuple[float, float]:
    """Scalar components derived from row-level factors (deterministic)."""
    if not enriched_rows:
        return 0.0, 0.0
    neg_w = 0.0
    inh_w = 0.0
    wsum = 0.0
    for r in enriched_rows:
        if not isinstance(r, dict):
            continue
        raw = float(r.get("raw_contradiction_score") or r.get("score") or 0.0)
        w = max(_EPS, raw)
        neg_w += w * float(r.get("negation_factor") or 0.0)
        inh_w += w * float(r.get("inhibition_factor") or 0.0)
        wsum += w
    inv = 1.0 / wsum
    return _clamp01(neg_w * inv), _clamp01(inh_w * inv)
