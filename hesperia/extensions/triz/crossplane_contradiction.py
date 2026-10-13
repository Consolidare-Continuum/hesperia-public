# HESPERIA — Cross-plane contradiction package (deterministic, v0.5.8 task4–5).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import math
from typing import Any

from core.math.basic_stats import clamp01 as _clamp01, mean as _mean, variance as _variance
from hesperia.engine.tfp_signal_calibration import load_tfp_signal_calibration
from hesperia.extensions.triz.contradiction_coupling import build_area_contradiction_pressure
from hesperia.extensions.triz.contradiction_negation import (
    build_contradiction_mode_summary,
    crossplane_negation_inhibition_components,
)
from hesperia.extensions.triz.family_contradiction import (
    build_family_contradiction_matrix,
    build_family_contradiction_pressure,
    compute_family_bridge_conflict,
    compute_family_fragmentation,
    family_conflict_concentration,
)
from hesperia.extensions.triz.contradiction_feedback import build_contradiction_feedback_signals
from hesperia.ontology.dictB.loader import build_concept_to_area_family

_EPS = 1e-15
CROSSPLANE_VERSION = "crossplane_task6"


def _row_activation_latent_lists(rows: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
    act_vals: list[float] = []
    lat_vals: list[float] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        raw = float(r.get("raw_contradiction_score") or r.get("score") or 0.0)
        if raw <= _EPS:
            continue
        ea = r.get("effective_activation_score")
        el = r.get("effective_latent_conflict_score")
        es = r.get("effective_score")
        if ea is not None:
            act_vals.append(float(ea))
        elif es is not None:
            act_vals.append(float(es))
        else:
            act_vals.append(raw)
        if el is not None:
            lat_vals.append(float(el))
        elif ea is not None:
            lat_vals.append(float(ea))
        elif es is not None:
            lat_vals.append(float(es))
        else:
            lat_vals.append(raw)
    return act_vals, lat_vals


def _mean_pair_confidence(rows: list[dict[str, Any]]) -> float:
    vals = [float(r.get("confidence") or 0.0) for r in rows if isinstance(r, dict) and r.get("confidence") is not None]
    return _mean(vals) if vals else 1.0


def _confidences_distribution(rows: list[dict[str, Any]]) -> dict[str, float]:
    vals = sorted(float(r.get("confidence") or 0.0) for r in rows if isinstance(r, dict))
    if not vals:
        return {"min": 0.0, "mean": 1.0, "max": 1.0}
    return {"min": round(vals[0], 6), "mean": round(_mean(vals), 6), "max": round(vals[-1], 6)}


def _lexical_semantic_split(
    uncertainty_package: dict[str, Any] | None,
    raw_load: float,
    eff_load: float,
    mean_conf: float,
) -> dict[str, float]:
    lex = float(uncertainty_package.get("lexical_uncertainty") or 0.0) if uncertainty_package else 0.0
    conu = float(uncertainty_package.get("concept_uncertainty") or 0.0) if uncertainty_package else 0.0
    gap = max(0.0, raw_load - eff_load)
    likely_lex = _clamp01(0.45 * lex + 0.35 * gap + 0.2 * (1.0 - mean_conf))
    likely_concept = _clamp01(0.55 * conu + 0.25 * (1.0 - mean_conf) + 0.2 * gap)
    likely_sem = _clamp01(max(0.0, eff_load * (0.35 + 0.65 * mean_conf)))
    s = likely_lex + likely_concept + likely_sem + _EPS
    return {
        "likely_lexical": round(likely_lex / s, 6),
        "likely_conceptual_ambiguity": round(likely_concept / s, 6),
        "likely_semantic_real": round(likely_sem / s, 6),
    }


def build_crossplane_contradiction_package(
    activation: dict[str, Any],
    topology: dict[str, Any] | None,
    contradictions: list[dict[str, Any]] | None,
    *,
    concept_to_area_family: dict[str, tuple[str, str]] | None = None,
    uncertainty_package: dict[str, Any] | None = None,
    contradiction_calibration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Single canonical contradiction signal for DLCR / sealed multiscale / product (04/05/06),
    aligned with topology (09) when ``topology`` is supplied.
    """
    cfg = load_tfp_signal_calibration()
    area_ids = [str(x) for x in (cfg.get("area_ids") or [])]
    af = concept_to_area_family if concept_to_area_family is not None else build_concept_to_area_family()
    topo = topology or {}
    act_cal = dict((contradiction_calibration or {}).get("activation") or {})

    rows = list(contradictions) if contradictions else []
    coupling_active = bool(activation.get("contradiction_coupling_active"))
    rp_act = activation.get("contradiction_pressure_raw") or {}
    ep_act = activation.get("contradiction_pressure") or {}
    raw_area_pressure: dict[str, float] = {a: float(rp_act.get(a, 0.0)) for a in area_ids}
    eff_area_pressure: dict[str, float] = {a: float(ep_act.get(a, 0.0)) for a in area_ids}
    if rows:
        eff_area_pressure = build_area_contradiction_pressure(
            rows, af, area_ids, use_effective_scores=True, activation_cal=act_cal
        )
        raw_area_pressure = build_area_contradiction_pressure(
            rows, af, area_ids, use_effective_scores=False, activation_cal=act_cal
        )

    area_pressure = eff_area_pressure
    seg_loads_raw = topo.get("segment_contradiction_loads") or []
    segment_contradiction_loads: list[dict[str, Any]] = []
    for item in seg_loads_raw:
        if isinstance(item, dict):
            segment_contradiction_loads.append(dict(sorted(item.items())))

    transition_pressure = [float(x) for x in (topo.get("transition_pressure") or []) if isinstance(x, (int, float))]

    loads_norm = [
        _clamp01(float(s.get("contradiction_load_normalized") or s.get("contradiction_load") or 0.0))
        for s in segment_contradiction_loads
    ]
    if not loads_norm and rows:
        g_fallback = _clamp01(max(area_pressure.values()) if area_pressure else 0.0)
        loads_norm = [g_fallback]

    effective_contradiction_load = _clamp01(
        _mean(loads_norm) if loads_norm else max(eff_area_pressure.values()) if eff_area_pressure else 0.0
    )
    raw_contradiction_load = _clamp01(
        max(raw_area_pressure.values()) if raw_area_pressure else effective_contradiction_load
    )

    cross_mass_sum = 0.0
    load_sum = 0.0
    for s in segment_contradiction_loads:
        cross_mass_sum += float(s.get("cross_area_contradiction_mass") or 0.0)
        load_sum += float(s.get("contradiction_load") or 0.0)
    if segment_contradiction_loads and load_sum > _EPS:
        cross_area_contradiction_mass = _clamp01(cross_mass_sum / load_sum)
    elif rows:
        cross_area_contradiction_mass = _clamp01(
            min(1.0, sum(area_pressure.values()) / (len(area_ids) * max(1.0, float(len(rows)))))
        )
    else:
        cross_area_contradiction_mass = 0.0

    var_l = _variance(loads_norm)
    mean_tp = _mean(transition_pressure) if transition_pressure else 0.0
    escalation = 0.0
    if len(loads_norm) >= 2:
        for i in range(1, len(loads_norm)):
            if loads_norm[i] > loads_norm[i - 1] + 1e-12:
                escalation += loads_norm[i] - loads_norm[i - 1]
        escalation = _clamp01(escalation / float(len(loads_norm) - 1))

    contradiction_stability_index = _clamp01(
        1.0
        - min(
            1.0,
            0.42 * mean_tp + 0.28 * min(1.0, var_l * 4.0) + 0.15 * escalation + 0.15 * effective_contradiction_load,
        )
    )

    topo_summary = (topo.get("curve_projection_meta") or {}).get("contradiction_summary") or {}
    topo_coupling_flag = bool(topo_summary.get("contradiction_coupling_active")) if topo_summary else bool(
        segment_contradiction_loads and rows
    )
    if not rows:
        contradiction_coherence_flag = True
    elif segment_contradiction_loads:
        contradiction_coherence_flag = bool(coupling_active == topo_coupling_flag)
    else:
        contradiction_coherence_flag = bool(coupling_active)

    mean_conf = _mean_pair_confidence(rows)
    lex_u = float(uncertainty_package.get("lexical_uncertainty") or 0.0) if uncertainty_package else 0.0
    un_adj = _clamp01(effective_contradiction_load * mean_conf * (1.0 - 0.22 * lex_u))

    split = _lexical_semantic_split(uncertainty_package, raw_contradiction_load, effective_contradiction_load, mean_conf)

    act_vals, lat_vals = _row_activation_latent_lists(rows)
    activation_conflict_load = _clamp01(_mean(act_vals) if act_vals else effective_contradiction_load)
    latent_conflict_load = _clamp01(_mean(lat_vals) if lat_vals else activation_conflict_load)
    contradiction_mode_summary = build_contradiction_mode_summary(rows)
    neg_comp, inh_comp = crossplane_negation_inhibition_components(rows)
    family_pressure = activation.get("family_contradiction_pressure_effective")
    if not isinstance(family_pressure, dict):
        family_pressure = build_family_contradiction_pressure(rows, af).get("effective") or {}
    family_matrix = activation.get("family_contradiction_matrix")
    if not isinstance(family_matrix, dict):
        family_matrix = build_family_contradiction_matrix(rows, af)
    family_to_area = {str(v[1]): str(v[0]) for v in af.values() if isinstance(v, tuple) and len(v) >= 2}
    family_fragment = activation.get("family_fragmentation_summary")
    if not isinstance(family_fragment, dict) or not family_fragment:
        family_fragment = compute_family_fragmentation(
            {str(k): float(v) for k, v in family_pressure.items()},
            activation.get("family_scores_post_contradiction") if isinstance(activation.get("family_scores_post_contradiction"), dict) else activation.get("families") if isinstance(activation.get("families"), dict) else {},
            family_to_area,
        )
        family_fragment.update(compute_family_bridge_conflict(family_matrix, family_to_area))
    family_bridge = compute_family_bridge_conflict(family_matrix, family_to_area)
    family_concentration = family_conflict_concentration(
        {str(k): float(v) for k, v in family_pressure.items()}
    )
    feedback = build_contradiction_feedback_signals(
        contradiction_rows=rows,
        uncertainty_package=uncertainty_package,
        activation=activation,
        lexical_output=None,
        top_k=20,
        contradiction_calibration=contradiction_calibration,
    )
    gfb = feedback.get("global_feedback_summary") or {}
    runtime_split = gfb.get("runtime_vs_calibration_conflict_split") or {}

    out: dict[str, Any] = {
        "crossplane_version": CROSSPLANE_VERSION,
        "global_contradiction_load": round(effective_contradiction_load, 6),
        "raw_contradiction_load": round(raw_contradiction_load, 6),
        "effective_contradiction_load": round(effective_contradiction_load, 6),
        "area_contradiction_pressure": {k: round(float(v), 6) for k, v in sorted(eff_area_pressure.items())},
        "area_contradiction_pressure_raw": {k: round(float(v), 6) for k, v in sorted(raw_area_pressure.items())},
        "cross_area_contradiction_mass": round(float(cross_area_contradiction_mass), 6),
        "segment_contradiction_loads": segment_contradiction_loads,
        "transition_pressure": [round(float(x), 6) for x in transition_pressure],
        "contradiction_stability_index": round(contradiction_stability_index, 6),
        "contradiction_coherence_flag": bool(contradiction_coherence_flag),
        "contradiction_coupling_active": bool(coupling_active or (rows and max(eff_area_pressure.values(), default=0.0) > _EPS)),
        "contradiction_confidence_mean": round(mean_conf, 6),
        "contradiction_confidence_distribution": _confidences_distribution(rows),
        "uncertainty_adjusted_conflict_index": round(un_adj, 6),
        "lexical_semantic_conflict_split": split,
        "activation_conflict_load": round(activation_conflict_load, 6),
        "latent_conflict_load": round(latent_conflict_load, 6),
        "contradiction_mode_summary": contradiction_mode_summary,
        "negation_conflict_component": round(neg_comp, 6),
        "inhibition_conflict_component": round(inh_comp, 6),
        "family_contradiction_pressure": {k: round(float(v), 6) for k, v in sorted(family_pressure.items())},
        "family_conflict_concentration": round(family_concentration, 6),
        "family_fragmentation_summary": family_fragment,
        "family_cross_area_bridge_mass": round(float(family_bridge.get("family_cross_area_bridge_mass") or 0.0), 6),
        "family_intra_area_conflict_mass": round(float(family_bridge.get("family_intra_area_conflict_mass") or 0.0), 6),
        "dominant_conflict_families": list(family_fragment.get("dominant_conflict_families") or []),
        "calibration_contradiction_risk": round(float(gfb.get("calibration_contradiction_risk") or 0.0), 6),
        "runtime_vs_calibration_conflict_split": {
            "likely_runtime_real": round(float(runtime_split.get("likely_runtime_real") or 0.0), 6),
            "likely_calibration_pathology": round(float(runtime_split.get("likely_calibration_pathology") or 0.0), 6),
        },
        "feedback_summary": {
            "high_risk_token_share": round(float(gfb.get("high_risk_token_share") or 0.0), 6),
            "high_risk_concept_share": round(float(gfb.get("high_risk_concept_share") or 0.0), 6),
            "high_risk_pair_share": round(float(gfb.get("high_risk_pair_share") or 0.0), 6),
        },
        "top_risky_concepts": list((feedback.get("concept_feedback") or {}).get("top_risky_concepts") or []),
        "top_risky_pairs": list((feedback.get("pair_feedback") or {}).get("top_risky_pairs") or []),
        "top_risky_tokens": list((feedback.get("lexical_feedback") or {}).get("top_risky_tokens") or []),
        "top_risky_families": list((feedback.get("family_feedback") or {}).get("top_risky_families") or []),
    }
    return out
