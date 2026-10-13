# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA Engine Dynamics — analyze: RAW_TEXT -> attribution -> guards -> SUMMARY.
Single execution entry point. Dict A/B via core.attribution.attribution_shared
(curated lexicon, lexicon/curated/A_CORE_STAR_MAP_v0_4_1_3.json + frozen B0/B1).

Core has no relation to any extension/module. The former "v06" attribution path
(core.attribution.attribution, a synthetic-placeholder dictionary — no real
vocabulary) has been retired; see core/attribution/_deprecated/README.md and
docs/foundations/attribution_layer.md. Sealed matrix is 0.7.0 + the sphereV
genesis areas/families (core/topology/invariant_catalog.py); real dictionaries
sourced from that same corpus are future work (not yet built).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

try:
    from core.attribution.attribution_shared import DEFAULT_TEXT_CAP, run_attribution_pipeline
    from core.propagation.guard_pipeline import run_pipeline as run_propagation_guard_pipeline
    from core.math.core_math import load_config, analyze as _core_analyze
    from core.propagation.output_contracts import to_minimal_operational_result
except ImportError:
    from attribution_shared import DEFAULT_TEXT_CAP, run_attribution_pipeline
    from guard_pipeline import run_pipeline as run_propagation_guard_pipeline
    from core_math import load_config, analyze as _core_analyze
    from output_contracts import to_minimal_operational_result


def _product_contradiction_extensions(
    minimal: dict[str, Any],
    extended: dict[str, Any],
    contradiction_package: dict[str, Any] | None,
) -> dict[str, Any]:
    """Structured product-layer contradiction metrics (06); no narrative patching."""
    if not contradiction_package:
        return {}
    g = float(contradiction_package.get("global_contradiction_load") or 0.0)
    raw_l = float(contradiction_package.get("raw_contradiction_load") or g)
    eff_l = float(contradiction_package.get("effective_contradiction_load") or g)
    mconf = float(contradiction_package.get("contradiction_confidence_mean") or 1.0)
    split = contradiction_package.get("lexical_semantic_conflict_split") or {}
    un_adj = float(contradiction_package.get("uncertainty_adjusted_conflict_index") or eff_l)
    coh_raw = None
    if isinstance(extended.get("dict_b"), dict):
        coh_raw = extended["dict_b"].get("coherence_index")
    try:
        coherence = float(coh_raw) if coh_raw is not None else 0.5
    except (TypeError, ValueError):
        coherence = 0.5
    gov = float(minimal.get("governance") if minimal.get("governance") is not None else minimal.get("constraint_status") or 0.0)
    dominance_overstates = eff_l > 0.42 and gov > 0.68 and coherence > 0.72 and mconf > 0.45
    topo_ok = bool(contradiction_package.get("contradiction_coherence_flag"))
    dlcr_ok = abs(eff_l - gov) < 0.38 or (eff_l > 0.22 and gov < 0.82)
    consistency_score = max(0.0, min(1.0, 1.0 - 0.55 * max(0.0, eff_l - coherence) * (0.55 + 0.45 * mconf)))
    product_conflict_consistency = {
        "dominance_overstates_coherence": bool(dominance_overstates),
        "topology_matches_conflict": bool(topo_ok),
        "dlcr_matches_conflict": bool(dlcr_ok),
        "consistency_score": round(consistency_score, 6),
    }
    conflict_visible = eff_l > 0.12
    verdict_under = eff_l > 0.48 and coherence > 0.74 and mconf > 0.5
    verdict_conflict_alignment = {
        "conflict_visible_in_verdict": bool(conflict_visible),
        "verdict_underreports_conflict": bool(verdict_under),
    }
    product_stability = float(contradiction_package.get("contradiction_stability_index") or 0.0)
    sem_rel = max(
        0.0,
        min(1.0, mconf * float(split.get("likely_semantic_real") or 0.5) + 0.15 * un_adj),
    )
    if raw_l > 0.58 and mconf < 0.42:
        session_mode = "ambiguous_or_contaminated_contradiction"
    elif eff_l > 0.65 and product_stability < 0.35 and mconf > 0.45:
        session_mode = "contradiction_heavy_unstable"
    elif eff_l > 0.55 and mconf > 0.48:
        session_mode = "conflict_dominant"
    elif eff_l > 0.2:
        session_mode = "conflict_bearing_interpretable"
    else:
        session_mode = "coherent"
    conflict_confidence_summary = {
        "raw_contradiction_load": round(raw_l, 6),
        "effective_contradiction_load": round(eff_l, 6),
        "mean_conflict_confidence": round(mconf, 6),
    }
    conflict_source_balance = {
        "lexical_noise_component": round(float(split.get("likely_lexical") or 0.0), 6),
        "concept_ambiguity_component": round(float(split.get("likely_conceptual_ambiguity") or 0.0), 6),
        "semantic_conflict_component": round(float(split.get("likely_semantic_real") or 0.0), 6),
    }
    act_cf = float(contradiction_package.get("activation_conflict_load") or eff_l)
    lat_cf = float(contradiction_package.get("latent_conflict_load") or act_cf)
    mode_sum = contradiction_package.get("contradiction_mode_summary") or {}
    neg_c = float(contradiction_package.get("negation_conflict_component") or 0.0)
    inh_c = float(contradiction_package.get("inhibition_conflict_component") or 0.0)
    conflict_mode_summary = dict(mode_sum) if isinstance(mode_sum, dict) else {}
    latent_vs_overt_conflict = {
        "overt_conflict_load": round(act_cf, 6),
        "latent_conflict_load": round(lat_cf, 6),
        "conflict_is_partly_suppressed": bool(lat_cf > act_cf + 0.06),
    }
    negation_inhibition_conflict_alignment = {
        "negation_visible_in_conflict_model": bool(neg_c > 0.08),
        "inhibition_visible_in_conflict_model": bool(inh_c > 0.08),
        "alignment_score": round(
            max(0.0, min(1.0, 1.0 - 0.5 * abs(act_cf - lat_cf) + 0.25 * min(neg_c, inh_c))),
            6,
        ),
    }
    fam_frag = contradiction_package.get("family_fragmentation_summary") or {}
    fam_conc = float(contradiction_package.get("family_conflict_concentration") or 0.0)
    fam_dom = list(contradiction_package.get("dominant_conflict_families") or [])
    family_conflict_summary = {
        "global_family_fragmentation": round(float(fam_frag.get("global_family_fragmentation") or 0.0), 6),
        "dominant_conflict_families": fam_dom,
        "family_conflict_concentration": round(fam_conc, 6),
    }
    family_vs_area_conflict_alignment = {
        "family_conflict_hidden_by_area_smoothing": bool(
            float(fam_frag.get("global_family_fragmentation") or 0.0) > 0.35 and eff_l < 0.25
        ),
        "alignment_score": round(
            max(
                0.0,
                min(
                    1.0,
                    1.0 - abs(float(fam_frag.get("global_family_fragmentation") or 0.0) - eff_l),
                ),
            ),
            6,
        ),
    }
    split = contradiction_package.get("runtime_vs_calibration_conflict_split") or {}
    conflict_origin_summary = {
        "likely_runtime_real": round(float(split.get("likely_runtime_real") or 0.0), 6),
        "likely_calibration_pathology": round(float(split.get("likely_calibration_pathology") or 0.0), 6),
    }
    raw_vs_effective_gap = abs(raw_l - eff_l)
    high_raw_low_conf = bool(raw_l > 0.52 and mconf < 0.42)
    conflict_confidence_consistency = not (
        high_raw_low_conf and session_mode == "conflict_dominant" and sem_rel > 0.72
    )
    from hesperia.extensions.triz.conflict_release_gating import compute_product_release_conflict_readiness

    release_conflict_readiness = compute_product_release_conflict_readiness(
        contradiction_package,
        session_mode=session_mode,
        verdict_conflict_alignment=verdict_conflict_alignment,
        semantic_conflict_reliability=sem_rel,
        conflict_confidence_consistency=conflict_confidence_consistency,
    )
    return {
        "contradiction_summary": {
            "global_load": round(g, 6),
            "cross_area_mass": round(float(contradiction_package.get("cross_area_contradiction_mass") or 0.0), 6),
            "stability_index": round(product_stability, 6),
            "coupling_active": bool(contradiction_package.get("contradiction_coupling_active")),
        },
        "conflict_confidence_summary": conflict_confidence_summary,
        "uncertainty_adjusted_conflict_index": round(un_adj, 6),
        "conflict_source_balance": conflict_source_balance,
        "semantic_conflict_reliability": round(sem_rel, 6),
        "product_conflict_consistency": product_conflict_consistency,
        "verdict_conflict_alignment": verdict_conflict_alignment,
        "product_stability_under_contradiction": round(max(0.0, min(1.0, product_stability * (1.0 - 0.35 * eff_l))), 6),
        "session_contradiction_mode": session_mode,
        "conflict_mode_summary": conflict_mode_summary,
        "latent_vs_overt_conflict": latent_vs_overt_conflict,
        "negation_inhibition_conflict_alignment": negation_inhibition_conflict_alignment,
        "family_conflict_summary": family_conflict_summary,
        "family_fragmentation_visibility": bool(family_conflict_summary["global_family_fragmentation"] > 0.08),
        "family_vs_area_conflict_alignment": family_vs_area_conflict_alignment,
        "conflict_origin_summary": conflict_origin_summary,
        "runtime_vs_calibration_conflict_split": conflict_origin_summary,
        "release_conflict_readiness": release_conflict_readiness,
    }


def _has_nan_inf(d: dict[str, Any]) -> bool:
    for v in d.values():
        if isinstance(v, (int, float)) and (math.isnan(v) or math.isinf(v)):
            return True
        if isinstance(v, dict) and _has_nan_inf(v):
            return True
    return False


# Ethan PO-02: spans match `schemas/lexical_concept/resolver_output.schema.json` (omit `audit` for payload size).
_PO02_MAX_EVIDENCE_SPANS = 24


def _public_dlcr_span_row(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    return {k: v for k, v in row.items() if k != "audit"}


def analyze(
    text: str,
    text_cap: int = DEFAULT_TEXT_CAP,
    shadow_enabled: bool | None = None,
    assets_root: Path | None = None,
    r1_r4: bool = False,
    r1_r4_book_id: str = "book",
    r1_r4_levels: list[str] | None = None,
    contradiction_package: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Run execution flow: TRANSFORM normalize -> TRANSFORM tokenize -> COMPUTE attribution -> COMPUTE core -> EVALUATE Sigma.
    Returns (SUMMARY, DIAGNOSTICS).

    When r1_r4=True, runs R1–R4 reading-scale pipeline and attaches
    extended["r1_r4"] = {"units": [...], "book_profile": {...}}.
    Ref: docs/R1_R4_INTEGRATION_CONTRACT.md (I2).
    """
    if not text or not str(text).strip():
        raise ValueError("text_missing")
    cfg = load_config()
    cap = int(cfg.get("text_cap", text_cap))
    shadow = shadow_enabled if shadow_enabled is not None else bool(cfg.get("shadow_enabled", False))
    dominant_family, dominant_area, seed, attr_metrics, extended = run_attribution_pipeline(
        text, cap=cap, assets_root=assets_root
    )
    family_vector = extended.get("family_vector") if isinstance(extended, dict) else None
    initial_S, initial_L = None, None
    if family_vector and len(family_vector) == 288:
        try:
            from core.math.core_math import perturb_shadow, reduce_288_to_5
            vec = list(family_vector)
            if shadow:
                vec = perturb_shadow(vec, cfg)
            initial_S, initial_L = reduce_288_to_5(vec)
        except Exception:
            pass
    raw = _core_analyze(initial_S=initial_S, initial_L=initial_L)
    raw["dominant_family"] = dominant_family
    raw["dominant_area"] = dominant_area
    result = run_propagation_guard_pipeline(
        raw,
        traversal_length=0,
        area_hop_count=0,
        evidence_count=1,
        shadow_enabled=shadow,
    )
    if _has_nan_inf(result):
        raise ValueError("metric_nan_inf")
    minimal = to_minimal_operational_result(result)
    extended_out = {
        "total_tokens": attr_metrics["total_tokens"],
        "matched_tokens": attr_metrics["matched_tokens"],
        "unmatched_tokens": attr_metrics["unmatched_tokens"],
        "attribution_coverage": attr_metrics["attribution_coverage"],
        "meanAltitude_global": attr_metrics["meanAltitude_global"],
        "seed_size": len(seed),
    }
    if isinstance(extended, dict):
        if extended.get("family_vector") and len(extended["family_vector"]) == 288:
            extended_out["family_vector"] = extended["family_vector"]
        if extended.get("family_vector_pre_sharpen") and len(extended["family_vector_pre_sharpen"]) == 288:
            extended_out["family_vector_pre_sharpen"] = extended["family_vector_pre_sharpen"]
    # Ethan PO-02: optional governed Dict A→B lexical evidence (DLCR pack), not legacy frozen dict alone.
    import os as _os_ev

    if _os_ev.environ.get("HESPERIA_ANALYZE_DLCR_EVIDENCE", "").strip().lower() in ("1", "true", "yes", "on"):
        try:
            _repo = Path(__file__).resolve().parents[2]
            from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

            snip = (text or "")[:8000]
            dlcr = run_dlcr_pipeline(
                snip,
                repo_root=_repo,
                mode="clinical_speech",
                contradiction_package=contradiction_package,
            )
            pm = dlcr.get("preprocess_meta") or {}
            raw_spans = dlcr.get("span_resolutions") or []
            pub_spans = [_public_dlcr_span_row(r) for r in raw_spans[:_PO02_MAX_EVIDENCE_SPANS]]
            extended_out["lexical_evidence_dlcr"] = {
                "analysis_text_fingerprint": pm.get("analysis_text_fingerprint"),
                "lexical_hits_accepted": dlcr.get("lexical_hits_accepted"),
                "lexical_hits_rejected": dlcr.get("lexical_hits_rejected"),
                "span_resolution_count": len(raw_spans),
                "resource_versions": dlcr.get("resource_versions"),
                "winning_concept_ids_sample": [
                    r.get("winning_concept_id") for r in raw_spans[:8]
                ],
                "evidence_spans": pub_spans,
                "evidence_spans_max": _PO02_MAX_EVIDENCE_SPANS,
                "evidence_spans_schema_id": "hesperia.schemas.lexical_concept.resolver_output.v0_6_0",
            }
        except Exception as e:
            extended_out["lexical_evidence_dlcr"] = {"_error": str(e)[:240]}
    if r1_r4:
        try:
            from runtime.pipeline.r1_r4_pipeline import run_full_pipeline
            levels = r1_r4_levels or ["R1", "R2", "R3", "R4"]
            units, book_profile = run_full_pipeline(
                text,
                book_id=r1_r4_book_id,
                assets_root=assets_root,
                levels=levels,
            )
            extended_out["r1_r4"] = {"units": units, "book_profile": book_profile}
        except Exception as e:
            extended_out["r1_r4"] = {"error": str(e), "units": [], "book_profile": None}
    if contradiction_package:
        extended_out.update(_product_contradiction_extensions(minimal, extended_out, contradiction_package))
    # KSI-Inspector neighbour lens (HES-MATH-BEHAV wire) — default off via HESPERIA_KSI_ENABLED.
    try:
        from core.domain.ksi.pipeline import attach_ksi_to_extended

        extended_out = attach_ksi_to_extended(extended_out, summary=minimal)
    except Exception as e:
        from core.domain.ksi.flags import ksi_enabled

        if ksi_enabled():
            extended_out["ksi"] = {"_error": str(e)[:240], "teacher_mode": "inspect_only"}
    return minimal, extended_out
