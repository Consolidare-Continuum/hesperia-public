# HESPERIA — LEVEL 10 Session topology (temporal dynamics of activation)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Dynamic session topology: segment by token windows, analyze per segment, retain raw
curves for audit, and apply deterministic temporal momentum before topology-derived
interpretation.
"""

from __future__ import annotations

import math
from typing import Any

from hesperia.engine.tfp_signal_calibration import (
    AREA_CURVE_MAP,
    CURVE_CALIBRATION_REFERENCE,
    DEFAULT_SESSION_TOPOLOGY_RUN_PARAMS,
    load_tfp_signal_calibration,
)
from hesperia.extensions.triz.topology_contradiction_coupling import (
    apply_contradiction_to_segment_areas,
    build_contradiction_coupling_summary,
    compute_segment_contradiction_loads,
    compute_transition_pressure,
    segment_momentum_factors_from_loads,
)
from research.clinical_tfp.interpretation import DEFENSE_MAP, detect_defense_pattern, get_dominant_area


def segment_session(text: str, window_size: int = 80) -> list[str]:
    if not text or not isinstance(text, str) or window_size < 1:
        return []
    from hesperia.nlp.session_parser import normalize_tokens, tokenize_text

    tokens = tokenize_text(text)
    normalized = normalize_tokens(tokens)
    if not normalized:
        return []
    return [
        " ".join(normalized[i : i + window_size])
        for i in range(0, len(normalized), window_size)
    ]


def analyze_session_segments(
    text: str,
    window_size: int = 80,
    marker_index: dict[str, list[tuple[str, float]]] | None = None,
    concept_to_area_family: dict[str, tuple[str, str]] | None = None,
    phrase_index: dict[str, dict[tuple[str, ...], list[tuple[str, float]]]] | None = None,
    normalize_scores: bool = True,
    contradiction_calibration: dict[str, Any] | None = None,
    **analyze_kwargs: Any,
) -> list[dict[str, Any]]:
    from hesperia.nlp.session_parser import analyze_session

    segments = segment_session(text, window_size=window_size)
    results: list[dict[str, Any]] = []
    for seg in segments:
        if not seg.strip():
            results.append({"areas": {}, "families": {}, "concepts": {}})
            continue
        r = analyze_session(
            seg,
            marker_index=marker_index,
            concept_to_area_family=concept_to_area_family,
            phrase_index=phrase_index,
            normalize_scores=normalize_scores,
            contradiction_calibration=contradiction_calibration,
            **analyze_kwargs,
        )
        results.append(
            {
                "areas": r.get("areas", {}),
                "areas_raw": r.get("areas_raw", {}),
                "areas_inhibited": r.get("areas_inhibited", {}),
                "families": r.get("families", {}),
                "families_pre_hex": r.get("families_pre_hex", {}),
                "families_post_hex": r.get("families_post_hex", {}),
                "family_contradiction_pressure_effective": r.get("family_contradiction_pressure_effective", {}),
                "family_fragmentation_summary": r.get("family_fragmentation_summary", {}),
                "concepts": r.get("concepts", {}),
                "concept_weights_raw": r.get("concept_weights_raw", {}),
                "concept_weights_post_hex": r.get("concept_weights_post_hex", {}),
                "hex_feedback_delta": r.get("hex_feedback_delta", {}),
                "invariant_activation": r.get("invariant_activation", {}),
            }
        )
    return results


def extract_area_curve(
    segment_results: list[dict[str, Any]],
    area_id: str,
    *,
    area_key: str = "areas",
) -> list[float]:
    out: list[float] = []
    for r in segment_results:
        raw = (r.get(area_key) or {}).get(area_id, 0.0)
        try:
            out.append(float(raw))
        except (TypeError, ValueError):
            out.append(0.0)
    return out


def build_area_curves(
    segment_results: list[dict[str, Any]],
    curve_map: dict[str, str] | None = None,
    *,
    area_key: str = "areas",
) -> dict[str, list[float]]:
    mapping = curve_map or AREA_CURVE_MAP
    return {
        name: extract_area_curve(segment_results, area_id, area_key=area_key)
        for name, area_id in mapping.items()
    }


def total_area_activation(areas: dict[str, Any]) -> float:
    total = 0.0
    for value in (areas or {}).values():
        try:
            total += max(0.0, float(value))
        except (TypeError, ValueError):
            continue
    return total


def normalize_areas_share_of_total(
    areas: dict[str, Any],
    eps: float = 1e-12,
) -> dict[str, float]:
    total = total_area_activation(areas)
    if total <= eps:
        return {str(key): 0.0 for key in (areas or {})}
    return {str(key): max(0.0, float(value)) / total for key, value in (areas or {}).items()}


# CHI-003-02: TFP-native "session working theme" — dual-signal alongside areas_final
# (invariant_activation.build_invariant_activation's whole-session cumulative softmax,
# unchanged). Per CHI-003-01 (Colombo verdict): areas_final answers "what accumulated the
# most mass all-session," which TFP_KERNBERG canon does not predict should be the ordinary
# in-session working theme (A10 = treatment-process/frame, not default hour content).
# areas_working down-weights the opening contract/frame-setting segments instead — a flat
# two-tier weight, not a Field Dynamics decay (no exponential state, no untuned Phase1Theta
# constants). Constants calibrated against the 14 real TFP sessions in
# outputs/tfp/runs/tfp_gena_*_corpuscalib (tests/fixtures/chi003_areas_working_calibration.json);
# see tests/test_areas_working_calibration.py for the calibration gate.
TFP_WORKING_THEME_WARMUP_SEGMENTS = 2
TFP_WORKING_THEME_WARMUP_WEIGHT = 0.25


def compute_areas_working(
    segment_results: list[dict[str, Any]],
    *,
    area_key: str = "areas",
    warmup_segments: int = TFP_WORKING_THEME_WARMUP_SEGMENTS,
    warmup_weight: float = TFP_WORKING_THEME_WARMUP_WEIGHT,
) -> dict[str, float]:
    """
    Session working theme: per-segment area shares averaged across the session, with the
    first ``warmup_segments`` segments (contract/frame-setting window) weighted by
    ``warmup_weight`` instead of 1.0. Returns {} if there are no segments.
    """
    agg: dict[str, float] = {}
    total_weight = 0.0
    for i, seg in enumerate(segment_results or []):
        weight = warmup_weight if i < warmup_segments else 1.0
        for area_id, value in ((seg or {}).get(area_key) or {}).items():
            try:
                agg[str(area_id)] = agg.get(str(area_id), 0.0) + weight * float(value)
            except (TypeError, ValueError):
                continue
        total_weight += weight
    if total_weight <= 1e-12:
        return {}
    return {area_id: value / total_weight for area_id, value in agg.items()}


def _float_or_skip(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def areas_to_positive_probs(areas: dict[str, Any]) -> list[float]:
    vals: list[float] = []
    for value in (areas or {}).values():
        fv = _float_or_skip(value)
        if fv is not None and fv > 0:
            vals.append(fv)
    total = sum(vals)
    if total <= 1e-15:
        return []
    return [x / total for x in vals]


def entropy_shannon(ps: list[float]) -> float:
    return -sum(p * math.log(p + 1e-15) for p in ps)


def dominance_confidence_from_areas(areas: dict[str, Any]) -> float:
    ps = areas_to_positive_probs(areas)
    if len(ps) < 2:
        return 0.62 if len(ps) == 1 else 0.35
    h = entropy_shannon(ps)
    h_max = math.log(len(ps))
    if h_max <= 1e-12:
        return 0.5
    return max(0.0, min(1.0, 1.0 - h / h_max))


def center_curves_by_session_mean(curves: dict[str, list[float]]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for name, series in curves.items():
        if not series:
            out[name] = []
            continue
        mu = sum(float(x) for x in series) / len(series)
        out[name] = [float(x) - mu for x in series]
    return out


def smooth_curve_adjacent(values: list[float], alpha_current: float = 0.7) -> list[float]:
    if not values:
        return []
    a = float(alpha_current)
    b = 1.0 - a
    out: list[float] = [float(values[0])]
    for i in range(1, len(values)):
        out.append(a * float(values[i]) + b * float(values[i - 1]))
    return out


def apply_temporal_momentum(
    segment_results: list[dict[str, Any]],
    *,
    alpha1: float,
    alpha2: float,
    segment_momentum_factors: list[float] | None = None,
) -> list[dict[str, Any]]:
    if not segment_results:
        return []
    area_ids = list(load_tfp_signal_calibration().get("area_ids") or [])
    stable_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(segment_results):
        factor = 1.0
        if segment_momentum_factors is not None and idx < len(segment_momentum_factors):
            factor = max(0.0, min(1.0, float(segment_momentum_factors[idx])))
        a1 = float(alpha1) * factor
        a2 = float(alpha2) * factor
        current = {aid: float((row.get("areas") or {}).get(aid, 0.0)) for aid in area_ids}
        prior_1 = stable_rows[idx - 1]["areas"] if idx >= 1 else {aid: 0.0 for aid in area_ids}
        prior_2 = stable_rows[idx - 2]["areas"] if idx >= 2 else {aid: 0.0 for aid in area_ids}
        combined = {
            aid: max(
                0.0,
                current.get(aid, 0.0)
                + a1 * float(prior_1.get(aid, 0.0))
                + a2 * float(prior_2.get(aid, 0.0)),
            )
            for aid in area_ids
        }
        total = sum(combined.values())
        if total > 1e-12:
            combined = {aid: combined[aid] / total for aid in area_ids}
        stable_rows.append({**row, "areas": combined, "areas_final": combined})
    return stable_rows


def postprocess_area_curves(
    segment_results: list[dict[str, Any]],
    curve_map: dict[str, str] | None = None,
    *,
    area_competition: str = "softmax",
    softmax_temperature: float = 1.0,
    smooth_alpha: float | None = None,
    session_center_curves: bool = True,
    include_dominance_confidence: bool = True,
    temporal_momentum: dict[str, float] | None = None,
    segment_momentum_factors: list[float] | None = None,
) -> tuple[dict[str, list[float]], dict[str, Any], dict[str, list[float]], list[dict[str, Any]]]:
    mapping = curve_map or AREA_CURVE_MAP
    cfg = load_tfp_signal_calibration()
    tm = temporal_momentum or dict(cfg.get("temporal_momentum") or {})
    stable_segments = apply_temporal_momentum(
        segment_results,
        alpha1=float(tm.get("alpha1") or 0.0),
        alpha2=float(tm.get("alpha2") or 0.0),
        segment_momentum_factors=segment_momentum_factors,
    )
    raw_curves = build_area_curves(segment_results, curve_map=mapping)
    stable_curves = build_area_curves(stable_segments, curve_map=mapping)
    conf_raw: list[float] = []
    conf_stable: list[float] = []
    if include_dominance_confidence:
        conf_raw = [dominance_confidence_from_areas(row.get("areas") or {}) for row in segment_results]
        conf_stable = [dominance_confidence_from_areas(row.get("areas") or {}) for row in stable_segments]
    if smooth_alpha is not None:
        stable_curves = {
            name: smooth_curve_adjacent(series, alpha_current=float(smooth_alpha))
            for name, series in stable_curves.items()
        }
    rel = center_curves_by_session_mean(stable_curves) if session_center_curves and stable_curves else {}
    meta: dict[str, Any] = {
        "area_competition": "invariant_softmax",
        "requested_area_competition": area_competition,
        "requested_softmax_temperature": float(softmax_temperature),
        "softmax_temperature": float(cfg.get("area_softmax_temperature") or 1.0),
        "smooth": None
        if smooth_alpha is None
        else {"mode": "adjacent_post_momentum", "alpha_current": float(smooth_alpha)},
        "session_center": "mean_subtracted_per_named_curve" if session_center_curves else None,
        "segment_dominance_confidence": conf_stable if include_dominance_confidence else None,
        "segment_dominance_confidence_raw": conf_raw if include_dominance_confidence else None,
        "segment_dominance_confidence_stable": conf_stable if include_dominance_confidence else None,
        "temporal_momentum": {
            "alpha1": float(tm.get("alpha1") or 0.0),
            "alpha2": float(tm.get("alpha2") or 0.0),
        },
        "area_curves_raw": raw_curves,
        "stable_segments": stable_segments,
    }
    return stable_curves, meta, rel, stable_segments


def _dominant_area(areas: dict[str, float]) -> str:
    if not areas:
        return ""
    return max(areas, key=lambda k: areas[k])


def detect_state_transitions(segment_results: list[dict[str, Any]]) -> list[list[str]]:
    if len(segment_results) < 2:
        return []
    prev = _dominant_area(segment_results[0].get("areas") or {})
    transitions: list[list[str]] = []
    for row in segment_results[1:]:
        curr = _dominant_area(row.get("areas") or {})
        if prev and curr and prev != curr:
            transitions.append([prev, curr])
        prev = curr
    return transitions


def detect_defense_shifts(
    segment_results: list[dict[str, Any]],
    defense_map: dict[str, str] | None = None,
) -> list[str]:
    mapping = defense_map or DEFENSE_MAP
    out: list[str] = []
    for row in segment_results:
        families = row.get("families") or {}
        defense = detect_defense_pattern(families, defense_map=mapping)
        out.append(defense if defense else "")
    return out


def detect_aggression_escalation(
    segment_results: list[dict[str, Any]],
    area_a4: str = "A4",
) -> list[float]:
    return extract_area_curve(segment_results, area_a4)


def build_session_state_sequence(segment_results: list[dict[str, Any]]) -> list[str]:
    return [_dominant_area(row.get("areas") or {}) for row in segment_results]


def run_session_topology(
    text: str,
    window_size: int = 80,
    marker_index: dict[str, list[tuple[str, float]]] | None = None,
    concept_to_area_family: dict[str, tuple[str, str]] | None = None,
    phrase_index: dict[str, dict[tuple[str, ...], list[tuple[str, float]]]] | None = None,
    normalize_scores: bool = True,
    *,
    contradictions: list[dict[str, Any]] | None = None,
    area_competition: str = "softmax",
    softmax_temperature: float = 1.0,
    curve_smooth_alpha: float | None = None,
    curve_session_center: bool = True,
    apply_token_negation: bool = True,
    negation_window: int = 2,
    negation_multiplier: float = 0.5,
    per_concept_score_cap: float | None = 8.0,
    use_log1p_concept_scores: bool = True,
    evidence_volume_normalize: bool = True,
    include_curve_projection_meta: bool = True,
    contradiction_calibration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = load_tfp_signal_calibration()
    tm = dict(cfg.get("temporal_momentum") or {})
    area_ids = [str(x) for x in (cfg.get("area_ids") or [])]
    if concept_to_area_family is not None:
        af = concept_to_area_family
    else:
        from hesperia.ontology.dictB.loader import build_concept_to_area_family

        af = build_concept_to_area_family()

    topo_cal = dict((contradiction_calibration or {}).get("topology") or {})

    segment_results = analyze_session_segments(
        text,
        window_size=window_size,
        marker_index=marker_index,
        concept_to_area_family=concept_to_area_family,
        phrase_index=phrase_index,
        normalize_scores=normalize_scores,
        apply_token_negation=apply_token_negation,
        negation_window=negation_window,
        negation_multiplier=negation_multiplier,
        per_concept_score_cap=per_concept_score_cap,
        use_log1p_concept_scores=use_log1p_concept_scores,
        evidence_volume_normalize=evidence_volume_normalize,
        contradictions=contradictions,
        contradiction_calibration=contradiction_calibration,
    )

    segment_contradiction_loads: list[dict[str, Any]] = []
    transition_pressure: list[float] = []
    segment_results_for_curves = segment_results
    segment_momentum_factors: list[float] | None = None
    contradiction_coupling_active = False
    contradiction_summary: dict[str, Any] = {}

    if contradictions:
        segment_contradiction_loads = compute_segment_contradiction_loads(
            segment_results,
            contradictions,
            af,
            area_ids,
            topology_cal=topo_cal,
        )
        transition_pressure = compute_transition_pressure(
            segment_contradiction_loads, area_ids, topology_cal=topo_cal
        )
        segment_results_for_curves, contradiction_coupling_active = apply_contradiction_to_segment_areas(
            segment_results,
            segment_contradiction_loads,
            area_ids,
            topology_cal=topo_cal,
        )
        segment_momentum_factors = segment_momentum_factors_from_loads(
            segment_contradiction_loads, topology_cal=topo_cal
        )
        contradiction_summary = build_contradiction_coupling_summary(
            segment_contradiction_loads,
            transition_pressure,
            contradiction_coupling_active,
        )

    area_curves_contradiction_adjusted = (
        build_area_curves(segment_results_for_curves) if contradictions else {}
    )

    area_curves_stable, cmeta, rel, stable_segments = postprocess_area_curves(
        segment_results_for_curves,
        area_competition=area_competition,
        softmax_temperature=softmax_temperature,
        smooth_alpha=curve_smooth_alpha,
        session_center_curves=bool(curve_session_center),
        include_dominance_confidence=True,
        temporal_momentum=tm,
        segment_momentum_factors=segment_momentum_factors,
    )
    area_curves_raw = build_area_curves(segment_results)
    segment_family_contradiction_pressure = [
        row.get("family_contradiction_pressure_effective", {}) if isinstance(row, dict) else {}
        for row in segment_results_for_curves
    ]
    segment_family_fragmentation = [
        float(((row.get("family_fragmentation_summary") or {}).get("global_family_fragmentation") or 0.0))
        if isinstance(row, dict)
        else 0.0
        for row in segment_results_for_curves
    ]
    segment_dominant_conflict_families = [
        list(((row.get("family_fragmentation_summary") or {}).get("dominant_conflict_families") or []))
        if isinstance(row, dict)
        else []
        for row in segment_results_for_curves
    ]
    out: dict[str, Any] = {
        "segments": segment_results,
        "segments_contradiction_adjusted": segment_results_for_curves,
        "segment_contradiction_loads": segment_contradiction_loads,
        "transition_pressure": transition_pressure,
        "segments_stable": stable_segments,
        "transitions": detect_state_transitions(stable_segments),
        "area_curves": area_curves_stable,
        "area_curves_raw": area_curves_raw,
        "area_curves_stable": area_curves_stable,
        "area_curves_contradiction_adjusted": area_curves_contradiction_adjusted,
        "segment_family_contradiction_pressure": segment_family_contradiction_pressure,
        "segment_family_fragmentation": segment_family_fragmentation,
        "segment_dominant_conflict_families": segment_dominant_conflict_families,
        "aggression_curve": area_curves_stable["aggression"],
        "aggression_curve_raw": area_curves_raw["aggression"],
        "state_sequence": build_session_state_sequence(stable_segments),
        "defense_timeline": detect_defense_shifts(stable_segments),
    }
    if curve_session_center and rel:
        out["area_curves_session_relative"] = rel
    if include_curve_projection_meta:
        cmeta = dict(cmeta)
        cmeta["contradiction_coupling_active"] = bool(contradictions and contradiction_coupling_active)
        cmeta["contradiction_coupling"] = {
            "version": "tfp_v0_5_8_task3",
            "contradiction_rows_supplied": len(contradictions or []),
        }
        cmeta["contradiction_summary"] = contradiction_summary if contradictions else {}
        out["curve_projection_meta"] = {
            **cmeta,
            "calibration_reference_bands": dict(CURVE_CALIBRATION_REFERENCE),
            "engine_params": {
                "window_size": window_size,
                "normalize_scores": normalize_scores,
                "area_competition": "invariant_softmax",
                "requested_area_competition": area_competition,
                "softmax_temperature": float(cfg.get("area_softmax_temperature") or 1.0),
                "requested_softmax_temperature": softmax_temperature,
                "curve_smooth_alpha": curve_smooth_alpha,
                "curve_session_center": curve_session_center,
                "apply_token_negation": apply_token_negation,
                "negation_window": negation_window,
                "negation_multiplier": negation_multiplier,
                "per_concept_score_cap": per_concept_score_cap,
                "use_log1p_concept_scores": use_log1p_concept_scores,
                "evidence_volume_normalize": evidence_volume_normalize,
                "include_curve_projection_meta": include_curve_projection_meta,
            },
            "area_curve_map": dict(AREA_CURVE_MAP),
            "lexical_controls": {
                "apply_token_negation": apply_token_negation,
                "negation_window": negation_window,
                "negation_multiplier": negation_multiplier,
                "per_concept_score_cap": per_concept_score_cap,
                "use_log1p_concept_scores": use_log1p_concept_scores,
                "evidence_volume_normalize": evidence_volume_normalize,
            },
            "temporal_momentum": {
                "alpha1": float(tm.get("alpha1") or 0.0),
                "alpha2": float(tm.get("alpha2") or 0.0),
            },
            "note": (
                "area_curves_raw are audit-only outputs from raw segment activations; "
                "area_curves and state_sequence use momentum-stabilized segment areas "
                "(contradiction-adjusted when contradiction rows are supplied)."
            ),
        }
    return out
