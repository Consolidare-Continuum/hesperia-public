# HESPERIA — Engine Dynamics invariant activation (markers → concepts → hex → areas).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.
#
# Mainline sealed path. Calibration loads from engine_signal_calibration (semantic_dynamics/).
# Legacy module name: hesperia.nlp.tfp_activation (compatibility shim only).

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.hexmap.dynamics import apply_decay, smooth_toward_mean
from core.hexmap.projection import project_concepts_to_hex
from hesperia.engine.engine_signal_calibration import AREA_IDS, load_engine_runtime_bundle
from hesperia.extensions.triz.contradiction_coupling import (
    apply_contradiction_coupling,
    build_area_contradiction_pressure,
    build_dynamic_inhibition_delta,
    count_contradiction_rows_used,
    enrich_contradiction_rows,
)
from hesperia.extensions.triz.contradiction_negation import (
    build_concept_inhibition_summary,
    build_negation_activation_summary,
)
from hesperia.extensions.triz.family_contradiction import (
    build_family_contradiction_matrix,
    build_family_contradiction_pressure,
    compute_family_bridge_conflict,
    compute_family_fragmentation,
    family_conflict_concentration,
)
from hesperia.nlp.semantic_state_update import (
    load_h_total,
    merge_propagated_with_evidence_off_index,
    update_semantic_state,
)
from hesperia.ontology.dictB.loader import build_concept_to_area_family

CONTRADICTION_COUPLING_VERSION = "contradiction_coupling_task6"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _load_anchor_registry() -> dict[str, str]:
    """Merge base anchors with the extended registry (legacy filename *tfp*)."""
    base = _repo_root() / "assets" / "data" / "engine_dynamics_v060" / "anchors"
    merged: dict[str, str] = {}
    for name in ("concept_hex_anchors.json", "concept_hex_anchors_tfp.json"):
        path = base / name
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            merged.update({str(k): str(v) for k, v in data.items()})
    return merged


def _round_sparse(d: dict[str, float], *, include_zero: bool = False) -> dict[str, float]:
    out: dict[str, float] = {}
    for key in sorted(d):
        val = float(d[key])
        if not include_zero and abs(val) < 1e-12:
            continue
        out[str(key)] = round(val, 6)
    return out


def _round_probability_vector(d: dict[str, float]) -> dict[str, float]:
    keys = [str(key) for key in AREA_IDS]
    rounded = {key: round(float(d.get(key, 0.0)), 6) for key in keys}
    total = sum(rounded.values())
    if total <= 1e-12:
        return rounded
    delta = round(1.0 - total, 6)
    if abs(delta) > 0.0:
        top_key = max(keys, key=lambda key: float(d.get(key, 0.0)))
        rounded[top_key] = round(rounded[top_key] + delta, 6)
    return rounded


def _concept_raw_sums(markers: list[tuple[str, float]]) -> dict[str, float]:
    sums: dict[str, float] = {}
    for cid, weight in markers:
        sums[str(cid)] = sums.get(str(cid), 0.0) + max(0.0, float(weight))
    return sums


def _stabilize_concepts(
    raw_concepts: dict[str, float],
    *,
    token_count: int,
    concept_cap: float,
    log_normalization_enabled: bool,
    segment_length_normalization: str,
) -> dict[str, float]:
    denom = 1.0
    if segment_length_normalization == "inverse_sqrt_token_count":
        denom = math.sqrt(float(max(token_count, 1)))
    out: dict[str, float] = {}
    for cid, raw in raw_concepts.items():
        capped = min(max(0.0, float(raw)), float(concept_cap))
        value = math.log1p(capped) if log_normalization_enabled else capped
        out[cid] = value / denom
    return out


def _aggregate_concepts(
    concept_weights: dict[str, float],
    concept_to_area_family: dict[str, tuple[str, str]],
) -> tuple[dict[str, float], dict[str, float]]:
    families: dict[str, float] = {}
    areas: dict[str, float] = {area_id: 0.0 for area_id in AREA_IDS}
    for cid, weight in concept_weights.items():
        af = concept_to_area_family.get(cid)
        if not af:
            continue
        area, family = af
        fkey = f"{area}_{family}"
        families[fkey] = families.get(fkey, 0.0) + float(weight)
        areas[area] = areas.get(area, 0.0) + float(weight)
    return families, areas


def _areas_from_families(families: dict[str, float], area_ids: list[str]) -> dict[str, float]:
    out: dict[str, float] = {str(a): 0.0 for a in area_ids}
    for fkey, value in families.items():
        area = str(fkey).split("_", 1)[0]
        if area in out:
            out[area] += float(value)
    return out


def _apply_hex_feedback(
    concept_weights: dict[str, float],
    *,
    hex_decay: float,
    hex_smoothing_alpha: float,
) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float], list[str]]:
    anchors = _load_anchor_registry()
    hex_raw, degradation_flags = project_concepts_to_hex(concept_weights, anchors)
    hex_post = apply_decay(hex_raw, decay=max(0.0, float(hex_decay)))
    if hex_smoothing_alpha > 0:
        hex_post = smooth_toward_mean(hex_post, alpha=min(1.0, float(hex_smoothing_alpha)))

    post_hex: dict[str, float] = {}
    delta: dict[str, float] = {}
    for cid, weight in concept_weights.items():
        anchor = anchors.get(cid)
        if not anchor:
            post_hex[cid] = float(weight)
            delta[cid] = 0.0
            continue
        raw_anchor = float(hex_raw.get(anchor) or 0.0)
        stable_anchor = float(hex_post.get(anchor) or 0.0)
        if raw_anchor <= 1e-12:
            scaled = float(weight)
        else:
            scaled = float(weight) * (stable_anchor / raw_anchor)
        post_hex[cid] = scaled
        delta[cid] = scaled - float(weight)
    return hex_raw, hex_post, post_hex, delta, degradation_flags


def _apply_area_inhibition(
    area_raw: dict[str, float],
    *,
    matrix: list[list[float]],
) -> dict[str, float]:
    vector = [max(0.0, float(area_raw.get(area_id, 0.0))) for area_id in AREA_IDS]
    inhibited: dict[str, float] = {}
    for i, area_id in enumerate(AREA_IDS):
        inhibition = 0.0
        for j in range(len(AREA_IDS)):
            inhibition += float(matrix[i][j]) * vector[j]
        inhibited[area_id] = max(0.0, vector[i] - inhibition)
    return inhibited


def _softmax_area_vector(area_values: dict[str, float], *, temperature: float) -> dict[str, float]:
    positives = [max(0.0, float(area_values.get(area_id, 0.0))) for area_id in AREA_IDS]
    if sum(positives) <= 1e-12:
        return {area_id: 0.0 for area_id in AREA_IDS}
    tau = max(float(temperature), 1e-6)
    mx = max(positives)
    exps = [math.exp((value - mx) / tau) for value in positives]
    denom = sum(exps) or 1.0
    return {area_id: exps[i] / denom for i, area_id in enumerate(AREA_IDS)}


def build_invariant_activation(
    markers: list[tuple[str, float]],
    *,
    token_count: int,
    concept_to_area_family: dict[str, tuple[str, str]] | None = None,
    embedding: dict[str, Any] | None = None,
    psi_prev: dict[str, float] | None = None,
    apply_semantic_state: bool = True,
    contradictions: list[dict[str, Any]] | None = None,
    uncertainty_package: dict[str, Any] | None = None,
    lexical_negation_summary: dict[str, Any] | None = None,
    contradiction_calibration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = load_engine_runtime_bundle()
    calibration = runtime["calibration"]
    inhibition_payload = runtime["inhibition_matrix"]
    af = concept_to_area_family if concept_to_area_family is not None else build_concept_to_area_family()

    raw_concepts = _concept_raw_sums(markers)
    stabilized_pre_hex = _stabilize_concepts(
        raw_concepts,
        token_count=token_count,
        concept_cap=float(calibration.get("concept_cap") or 8.0),
        log_normalization_enabled=bool(calibration.get("log_normalization_enabled")),
        segment_length_normalization=str(calibration.get("segment_length_normalization") or ""),
    )
    sdyn = calibration.get("semantic_dynamics") or {}
    semantic_on = bool(apply_semantic_state and sdyn.get("operator_enabled"))
    h_total: dict[str, Any] | None = None
    concepts_into_hex = stabilized_pre_hex
    psi_next: dict[str, float] | None = None
    semantic_segment_audit: dict[str, Any] | None = None

    if semantic_on:
        rel = str(sdyn.get("h_total_relative_path") or "semantic_dynamics/h_total_concepts.json")
        h_path = _repo_root() / "assets" / "data" / "engine_dynamics_v060" / rel
        try:
            h_total = dict(load_h_total(str(h_path)))
            alpha = float(sdyn.get("alpha") or 0.7)
            sat_k = float(sdyn.get("sat_k") or 1.2)
            prune_eps = float(sdyn.get("prune_eps") or 0.03)
            psi_next, semantic_segment_audit = update_semantic_state(
                psi_prev,
                stabilized_pre_hex,
                h_total,
                alpha=alpha,
                sat_k=sat_k,
                prune_eps=prune_eps,
            )
            concept_index = [str(x) for x in (h_total.get("concept_index") or [])]
            concepts_into_hex = merge_propagated_with_evidence_off_index(
                psi_next,
                stabilized_pre_hex,
                concept_index,
            )
        except (OSError, ValueError, TypeError, KeyError) as exc:
            semantic_on = False
            semantic_segment_audit = {
                "operator_applied": False,
                "error": str(exc),
            }

    families_pre_hex, areas_pre_hex = _aggregate_concepts(concepts_into_hex, af)
    hex_raw, hex_post, concepts_post_hex, hex_delta, degradation_flags = _apply_hex_feedback(
        concepts_into_hex,
        hex_decay=float(calibration.get("hex_decay") or 0.0),
        hex_smoothing_alpha=float(calibration.get("hex_smoothing_alpha") or 0.0),
    )
    families_post_hex, areas_raw = _aggregate_concepts(concepts_post_hex, af)
    family_scores_pre_contradiction = dict(families_post_hex)
    base_matrix = list(inhibition_payload.get("matrix") or [])

    neg_act_summary = build_negation_activation_summary(
        concepts_into_hex,
        concepts_post_hex,
        hex_delta,
        lexical_negation_summary,
    )
    inh_summary = build_concept_inhibition_summary(
        concepts_into_hex,
        concepts_post_hex,
        hex_delta,
        af,
        list(AREA_IDS),
    )

    use_contradiction_coupling = bool(contradictions)
    used_rows = 0
    pressure_map = {a: 0.0 for a in AREA_IDS}
    zero_delta = [[0.0 for _ in AREA_IDS] for _ in AREA_IDS]
    inhibition_matrix_dynamic = [list(row) for row in base_matrix] if base_matrix else zero_delta
    dynamic_delta_out = zero_delta
    areas_pressure_adjusted = dict(areas_raw)

    act_cal = dict((contradiction_calibration or {}).get("activation") or {})
    fam_cal = dict((contradiction_calibration or {}).get("family") or {})

    if use_contradiction_coupling:
        enriched = enrich_contradiction_rows(
            contradictions,
            uncertainty_package,
            concepts_post_hex,
            concept_weights_stabilized=concepts_into_hex,
            hex_feedback_delta=hex_delta,
            lexical_negation_summary=lexical_negation_summary,
            concept_to_area_family=af,
            contradiction_calibration=contradiction_calibration,
        )
        fam_pressure = build_family_contradiction_pressure(enriched, af)
        fam_effective = fam_pressure.get("effective") or {}
        fam_inf = float(act_cal.get("family_contradiction_influence", 1.0))
        family_scores_post_contradiction: dict[str, float] = {}
        for fam, val in family_scores_pre_contradiction.items():
            p = min(1.0, max(0.0, float(fam_effective.get(str(fam), 0.0))) * fam_inf)
            family_scores_post_contradiction[str(fam)] = max(0.0, float(val) * (1.0 - p))
        areas_raw = _areas_from_families(family_scores_post_contradiction, list(AREA_IDS))
        used_rows = count_contradiction_rows_used(enriched, af, AREA_IDS)
        pressure_map_raw = build_area_contradiction_pressure(
            enriched, af, AREA_IDS, use_effective_scores=False, activation_cal=act_cal
        )
        pressure_map = build_area_contradiction_pressure(
            enriched, af, AREA_IDS, use_effective_scores=True, activation_cal=act_cal
        )
        dynamic_delta_raw = build_dynamic_inhibition_delta(
            enriched, af, AREA_IDS, use_effective_scores=False, activation_cal=act_cal
        )
        dynamic_delta_out = build_dynamic_inhibition_delta(
            enriched,
            af,
            AREA_IDS,
            use_effective_scores=True,
            use_latent_scores=True,
            activation_cal=act_cal,
        )
        coupled = apply_contradiction_coupling(
            areas_raw,
            base_matrix,
            pressure_map,
            dynamic_delta_out,
            AREA_IDS,
            inhibition_scale=1.0,
        )
        areas_pressure_adjusted = coupled["areas_pressure_adjusted"]
        areas_inhibited = coupled["areas_inhibited"]
        inhibition_matrix_dynamic = coupled["inhibition_matrix_dynamic"]
        dynamic_delta_out = coupled["dynamic_inhibition_delta"]
        concept_participation: dict[str, int] = {}
        family_participation: dict[str, int] = {}
        for row in enriched:
            pair = row.get("pair")
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                for c in (str(pair[0]), str(pair[1])):
                    concept_participation[c] = concept_participation.get(c, 0) + 1
            fa = str(row.get("family_a") or "")
            fb = str(row.get("family_b") or "")
            if fa:
                family_participation[fa] = family_participation.get(fa, 0) + 1
            if fb:
                family_participation[fb] = family_participation.get(fb, 0) + 1
    else:
        areas_inhibited = _apply_area_inhibition(
            areas_raw,
            matrix=base_matrix,
        )
        fam_pressure = {"raw": {}, "effective": {}}
        family_scores_post_contradiction = dict(family_scores_pre_contradiction)
        enriched = []
        concept_participation = {}
        family_participation = {}

    coupling_effective = bool(use_contradiction_coupling and used_rows > 0)
    areas_final = _softmax_area_vector(
        areas_inhibited,
        temperature=float(calibration.get("area_softmax_temperature") or 1.0),
    )

    activation: dict[str, Any] = {
        "concepts": _round_sparse(concepts_post_hex),
        "families": _round_sparse(family_scores_post_contradiction),
        "areas": _round_probability_vector(areas_final),
        "areas_raw": _round_sparse(areas_raw, include_zero=True),
        "areas_inhibited": _round_sparse(areas_inhibited, include_zero=True),
        "areas_final": _round_probability_vector(areas_final),
        "areas_pre_hex": _round_sparse(areas_pre_hex, include_zero=True),
        "families_pre_hex": _round_sparse(families_pre_hex),
        "families_post_hex": _round_sparse(families_post_hex),
        "family_scores_pre_contradiction": _round_sparse(family_scores_pre_contradiction, include_zero=True),
        "family_scores_post_contradiction": _round_sparse(family_scores_post_contradiction, include_zero=True),
        "concept_weights_raw": _round_sparse(raw_concepts),
        "concept_weights_stabilized": _round_sparse(stabilized_pre_hex),
        "concept_weights_post_hex": _round_sparse(concepts_post_hex),
        "hex_feedback_delta": _round_sparse(hex_delta),
        "hex_activation_raw": _round_sparse(hex_raw),
        "hex_activation_post": _round_sparse(hex_post),
        "contradiction_pressure": _round_sparse(pressure_map, include_zero=True),
        "family_contradiction_pressure_raw": _round_sparse(
            {str(k): float(v) for k, v in (fam_pressure.get("raw") or {}).items()},
            include_zero=True,
        ),
        "family_contradiction_pressure_effective": _round_sparse(
            {str(k): float(v) for k, v in (fam_pressure.get("effective") or {}).items()},
            include_zero=True,
        ),
        "areas_pressure_adjusted": _round_sparse(areas_pressure_adjusted, include_zero=True),
        "dynamic_inhibition_delta": [
            [round(float(dynamic_delta_out[i][j]), 6) for j in range(len(AREA_IDS))]
            for i in range(len(AREA_IDS))
        ],
        "inhibition_matrix_dynamic": [
            [round(float(inhibition_matrix_dynamic[i][j]), 6) for j in range(len(AREA_IDS))]
            for i in range(len(AREA_IDS))
        ],
        "contradiction_coupling_active": coupling_effective,
        "contradiction_count_used": int(used_rows),
        "family_contradiction_matrix": build_family_contradiction_matrix(enriched, af),
        "family_fragmentation_summary": {},
        "concept_contradiction_participation_counts": {
            k: int(concept_participation[k]) for k in sorted(concept_participation)
        },
        "family_contradiction_participation_counts": {
            k: int(family_participation[k]) for k in sorted(family_participation)
        },
        "negation_activation_summary": neg_act_summary,
        "concept_inhibition_summary": inh_summary,
        "invariant_activation": {
            "path_id": str(calibration.get("invariant_path_id") or "unknown"),
            "config_version": str(calibration.get("version") or "unknown"),
            "inhibition_matrix_version": str(inhibition_payload.get("version") or "unknown"),
            "inhibition_matrix_dynamic_version": (
                f"{inhibition_payload.get('version') or 'unknown'}+contradiction_delta"
                if use_contradiction_coupling
                else str(inhibition_payload.get("version") or "unknown")
            ),
            "area_softmax_temperature": float(calibration.get("area_softmax_temperature") or 1.0),
            "concept_cap": float(calibration.get("concept_cap") or 8.0),
            "log_normalization_enabled": bool(calibration.get("log_normalization_enabled")),
            "segment_length_normalization": str(
                calibration.get("segment_length_normalization") or "inverse_sqrt_token_count"
            ),
            "hex_feedback_active": bool(calibration.get("hex_feedback_required")),
            "hex_decay": float(calibration.get("hex_decay") or 0.0),
            "hex_smoothing_alpha": float(calibration.get("hex_smoothing_alpha") or 0.0),
            "token_count": int(max(token_count, 0)),
            "marker_count": len(markers),
            "degradation_flags": list(degradation_flags),
            "semantic_state_operator_enabled": bool(semantic_on),
            "contradiction_coupling_version": CONTRADICTION_COUPLING_VERSION,
            "contradiction_coupling_mode": (
                "area_pressure_and_dynamic_inhibition" if use_contradiction_coupling else "none"
            ),
            "contradiction_coupling_active": coupling_effective,
            "contradiction_count_used": int(used_rows),
        },
    }

    if use_contradiction_coupling:
        activation["contradiction_pressure_raw"] = _round_sparse(pressure_map_raw, include_zero=True)
        activation["dynamic_inhibition_delta_raw"] = [
            [round(float(dynamic_delta_raw[i][j]), 6) for j in range(len(AREA_IDS))]
            for i in range(len(AREA_IDS))
        ]
        family_to_area = {str(v[1]): str(v[0]) for v in af.values() if isinstance(v, tuple) and len(v) >= 2}
        frag_inf = float(fam_cal.get("family_fragmentation_influence", 1.0))
        fam_eff_scaled = {
            str(k): min(1.0, float(v) * frag_inf) for k, v in (fam_pressure.get("effective") or {}).items()
        }
        frag = compute_family_fragmentation(
            fam_eff_scaled,
            family_scores_post_contradiction,
            family_to_area,
        )
        bridge = compute_family_bridge_conflict(activation["family_contradiction_matrix"], family_to_area)
        bridge_inf = float(fam_cal.get("family_bridge_influence", 1.0))
        if abs(bridge_inf - 1.0) > 1e-12:
            bridge = {
                k: round(min(1.0, float(v) * bridge_inf), 6)
                for k, v in bridge.items()
                if isinstance(v, (int, float))
            }
        activation["family_fragmentation_summary"] = {
            **frag,
            **bridge,
            "family_conflict_concentration": family_conflict_concentration(
                {str(k): float(v) for k, v in (fam_pressure.get("effective") or {}).items()}
            ),
        }
    if uncertainty_package:
        activation["contradiction_uncertainty_package"] = dict(uncertainty_package)

    if semantic_segment_audit is not None:
        activation["semantic_state"] = semantic_segment_audit
    if semantic_on and psi_next is not None:
        activation["psi_concepts"] = _round_sparse(psi_next, include_zero=True)

    if embedding is not None:
        try:
            from sphere.topology.activation_propagation import propagate_activation

            prop = propagate_activation(
                {
                    "concepts": activation["concepts"],
                    "families": activation["families"],
                    "areas": activation["areas"],
                },
                embedding,
                propagation_trace=True,
            )
            activation["propagation_trace"] = prop.get("propagation_trace", [])
            activation["families_propagated"] = _round_sparse(prop.get("families") or {})
            activation["areas_propagated"] = _round_sparse(prop.get("areas") or {}, include_zero=True)
        except Exception as exc:  # noqa: BLE001
            activation["propagation_trace_error"] = str(exc)

    return activation


# Deprecated name (historical); prefer build_invariant_activation.
build_invariant_tfp_activation = build_invariant_activation
