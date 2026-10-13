#!/usr/bin/env python3
# HESPERIA — Cross-plane contradiction audit for TFP bundle outputs (v0.5.8 task4).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Load 04/05/06/09 session artifacts and report contradiction coherence flags."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from hesperia.extensions.triz.contradiction_calibration import (
    calibration_payload_sha256,
    get_default_contradiction_calibration,
    load_contradiction_calibration,
    validate_contradiction_calibration,
)
from hesperia.extensions.triz.contradiction_contract import validate_contradiction_contract
from hesperia.extensions.triz.conflict_release_gating import (
    build_conflict_release_summary,
    build_release_conflict_gates,
    evaluate_conflict_integrity,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _resolve_calibration_profile(
    bundle_dir: Path,
    d20: dict[str, Any] | None,
    manifest: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Returns ``(profile, audit)`` where audit contains inspector calibration visibility flags.
    """
    _ = bundle_dir
    snap = (d20 or {}).get("contradiction_calibration_snapshot") if isinstance(d20, dict) else None
    audit: dict[str, Any] = {
        "contradiction_calibration_valid": False,
        "missing_contradiction_calibration_sections": [],
        "invalid_contradiction_calibration_values": [],
        "contradiction_calibration_trace_visible": False,
        "calibration_profile_mismatch": False,
    }

    profile = get_default_contradiction_calibration()
    if isinstance(snap, dict):
        audit["contradiction_calibration_trace_visible"] = bool(snap.get("sha256") and snap.get("path"))
        path_hint = snap.get("path")
        exp_sha = str(snap.get("sha256") or "")
        if path_hint:
            candidate = Path(str(path_hint))
            if not candidate.is_file():
                candidate = _REPO_ROOT / str(path_hint).lstrip("/")
            if candidate.is_file():
                try:
                    profile = load_contradiction_calibration(candidate)
                    if exp_sha and calibration_payload_sha256(profile) != exp_sha:
                        audit["calibration_profile_mismatch"] = True
                except (OSError, ValueError, TypeError) as exc:
                    audit["invalid_contradiction_calibration_values"].append(str(exc))
            else:
                audit["missing_contradiction_calibration_sections"].append(str(path_hint))

    val = validate_contradiction_calibration(profile)
    audit["contradiction_calibration_valid"] = bool(val["ok"])
    if not val["ok"]:
        audit["invalid_contradiction_calibration_values"].extend(list(val["errors"]))

    if isinstance(manifest, dict) and manifest.get("contradiction_calibration_snapshot"):
        m_snap = manifest["contradiction_calibration_snapshot"]
        if isinstance(m_snap, dict) and isinstance(snap, dict) and m_snap.get("sha256") != snap.get("sha256"):
            audit["calibration_profile_mismatch"] = True

    return profile, audit


def _session_map(blob: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not blob:
        return {}
    sessions = blob.get("sessions")
    if not isinstance(sessions, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in sessions:
        if isinstance(row, dict) and row.get("session_id") is not None:
            out[str(row["session_id"])] = row
    return out


def inspect_bundle(bundle_dir: Path) -> dict[str, Any]:
    d04 = _load(bundle_dir / "04_dlcr_full.json")
    d05 = _load(bundle_dir / "05_sealed_multiscale.json")
    d06 = _load(bundle_dir / "06_product_analyze.json")
    d09 = _load(bundle_dir / "09_session_topology.json")
    d20 = _load(bundle_dir / "20_main_engine_full_context.json")
    d00 = _load(bundle_dir / "00_manifest.json")

    m04 = _session_map(d04)
    m05 = _session_map(d05)
    m06 = _session_map(d06)
    m09 = _session_map(d09)
    sids = sorted(set(m04) | set(m05) | set(m06) | set(m09))

    per_session: list[dict[str, Any]] = []
    session_flag_rows: list[dict[str, Any]] = []
    for sid in sids:
        row04 = m04.get(sid) or {}
        row05 = m05.get(sid) or {}
        row06 = m06.get(sid) or {}
        row09 = m09.get(sid) or {}
        st = (row09.get("session_topology") or {}) if isinstance(row09, dict) else {}
        meta = (st.get("curve_projection_meta") or {}).get("contradiction_summary") or {}
        g_topo = float(meta.get("max_segment_contradiction_load") or 0.0)
        cpkg_raw = row04.get("crossplane_contradiction_package")
        cpkg = cpkg_raw if isinstance(cpkg_raw, dict) else {}
        pkg_g = float(row04.get("contradiction_load") or 0.0)
        if cpkg.get("global_contradiction_load") is not None:
            pkg_g = max(pkg_g, float(cpkg.get("global_contradiction_load") or 0.0))
        raw_l = float(cpkg.get("raw_contradiction_load") or 0.0)
        eff_l = float(cpkg.get("effective_contradiction_load") or pkg_g)
        mconf = float(cpkg.get("contradiction_confidence_mean") or 1.0)
        raw_vs_effective_gap = abs(raw_l - eff_l)
        ext = (row06.get("extended") or {}) if isinstance(row06.get("extended"), dict) else {}
        vca = ext.get("verdict_conflict_alignment") or {}
        under = bool(vca.get("verdict_underreports_conflict"))
        mode = str(ext.get("session_contradiction_mode") or "")
        sem_rel = float(ext.get("semantic_conflict_reliability") or 0.0)
        cfs = ext.get("conflict_confidence_summary") or {}
        dlcr_align = row04.get("dlcr_contradiction_alignment") or {}
        spread_ok = bool(dlcr_align.get("spread_vs_contradiction_consistent"))
        sealed_trace = row05.get("sealed_conflict_trace") or {}
        collapse = bool(sealed_trace.get("conflict_collapses_under_aggregation"))
        persistent = bool(sealed_trace.get("persistent_conflict"))

        product_underreports_conflict = bool(g_topo > 0.45 and mode == "coherent" and not under)
        dlcr_conflict_misalignment = bool(row04.get("contradiction_load") is not None and not spread_ok and pkg_g > 0.35)
        multiscale_conflict_collapse = bool(persistent and collapse and pkg_g > 0.4)

        high_raw_low_conf = bool(raw_l > 0.52 and mconf < 0.42)
        likely_lexical_contamination = bool(raw_vs_effective_gap > 0.32 and mconf < 0.48)
        likely_concept_ambiguity_overdrive = bool(
            float((ext.get("conflict_source_balance") or {}).get("concept_ambiguity_component") or 0.0) > 0.45
            and eff_l < 0.35
        )
        conflict_confidence_consistency = not (
            high_raw_low_conf and mode == "conflict_dominant" and sem_rel > 0.72
        )
        neg_ms = cpkg.get("contradiction_mode_summary") or {}
        act_cf = float(cpkg.get("activation_conflict_load") or eff_l)
        lat_cf = float(cpkg.get("latent_conflict_load") or act_cf)
        neg_comp = float(cpkg.get("negation_conflict_component") or 0.0)
        inh_comp = float(cpkg.get("inhibition_conflict_component") or 0.0)
        dlr_neg = row04.get("negation_summary") if isinstance(row04.get("negation_summary"), dict) else {}
        neg_mark = float(dlr_neg.get("negated_marker_ratio") or 0.0)
        lvo = ext.get("latent_vs_overt_conflict") or {}
        fam_frag = cpkg.get("family_fragmentation_summary") or {}
        fam_global = float(fam_frag.get("global_family_fragmentation") or 0.0)
        fam_conc = float(cpkg.get("family_conflict_concentration") or 0.0)
        fam_bridge = float(cpkg.get("family_cross_area_bridge_mass") or 0.0)
        runtime_split = cpkg.get("runtime_vs_calibration_conflict_split") or {}
        likely_cal = float(runtime_split.get("likely_calibration_pathology") or 0.0)
        likely_run = float(runtime_split.get("likely_runtime_real") or 0.0)
        top_pairs = cpkg.get("top_risky_pairs") if isinstance(cpkg.get("top_risky_pairs"), list) else []
        persistent_low_conflict_confidence_pairs = [
            p
            for p in top_pairs
            if float((p or {}).get("effective_conflict") or 0.0) < 0.35
            and float((p or {}).get("pair_recurrence") or 0.0) > 0.5
        ]
        negation_conflict_misalignment = bool(
            eff_l > 0.42 and neg_mark > 0.32 and float(neg_ms.get("negated_opposition_share") or 0.0) < 0.08
        )
        latent_conflict_underreported = bool(act_cf < 0.22 and lat_cf > 0.48 and mode == "coherent")
        coactive_conflict_overclaimed = bool(
            mode in {"conflict_dominant", "conflict_bearing_interpretable"}
            and float(neg_ms.get("inhibited_opposition_share") or 0.0)
            + float(neg_ms.get("negated_opposition_share") or 0.0)
            > 0.55
        )
        suppressed_conflict_disappearance = bool(
            inh_comp > 0.32
            and float(lvo.get("overt_conflict_load") or 0.0) < 0.18
            and float(lvo.get("latent_conflict_load") or 0.0) < 0.12
        )
        family_fragmentation_hidden = bool(fam_global > 0.4 and eff_l < 0.22 and mode == "coherent")
        family_conflict_underreported = bool(fam_global > 0.35 and not under and mode == "coherent")
        cross_area_bridge_underreported = bool(fam_bridge > 0.3 and g_topo < 0.2 and mode == "coherent")
        concentrated_family_conflict_omitted = bool(fam_conc > 0.6 and not cpkg.get("dominant_conflict_families"))
        family_matrix_collapse = bool((cpkg.get("family_contradiction_pressure") or {}) and fam_global <= 0.01)
        calibration_pathology_masquerading_runtime = bool(
            raw_l > 0.45 and mconf < 0.45 and likely_cal > 0.45 and mode in {"conflict_dominant", "conflict_bearing_interpretable"}
        )
        feedback_trace_missing = bool(
            (eff_l > 0.35 or fam_global > 0.35)
            and not cpkg.get("feedback_summary")
            and not cpkg.get("top_risky_concepts")
            and not cpkg.get("top_risky_pairs")
        )
        recommended_calibration_action = (
            "review_fuzzy_links_alias_routes_and_ambiguous_bridges"
            if feedback_trace_missing or calibration_pathology_masquerading_runtime or family_conflict_underreported
            else "none"
        )
        family_area_alignment_score = max(0.0, min(1.0, 1.0 - abs(fam_global - eff_l)))
        conflict_mode_consistency = bool(
            not negation_conflict_misalignment
            and not latent_conflict_underreported
            and not coactive_conflict_overclaimed
            and not suppressed_conflict_disappearance
            and not family_conflict_underreported
            and not family_fragmentation_hidden
            and not cross_area_bridge_underreported
            and not family_matrix_collapse
            and not calibration_pathology_masquerading_runtime
            and not feedback_trace_missing
        )
        latent_vs_overt_mismatch_warn = bool(
            float(lvo.get("latent_conflict_load") or 0.0) > float(lvo.get("overt_conflict_load") or 0.0) + 0.12
            and mode == "coherent"
        )
        crossplane_ok = not (
            product_underreports_conflict
            or dlcr_conflict_misalignment
            or multiscale_conflict_collapse
            or (likely_lexical_contamination and sem_rel > 0.75 and mode == "coherent")
            or negation_conflict_misalignment
            or latent_conflict_underreported
            or coactive_conflict_overclaimed
            or suppressed_conflict_disappearance
            or family_conflict_underreported
            or family_fragmentation_hidden
            or cross_area_bridge_underreported
            or concentrated_family_conflict_omitted
            or family_matrix_collapse
            or calibration_pathology_masquerading_runtime
            or feedback_trace_missing
        )
        session_flags: dict[str, Any] = {
            "session_id": sid,
            "topology_max_segment_contradiction_load": g_topo,
            "product_session_mode": mode,
            "effective_contradiction_load": eff_l,
            "raw_contradiction_load": raw_l,
            "semantic_conflict_reliability": sem_rel,
            "verdict_underreports_conflict_reported": under,
            "product_underreports_conflict": product_underreports_conflict,
            "dlcr_conflict_misalignment": dlcr_conflict_misalignment,
            "multiscale_conflict_collapse": multiscale_conflict_collapse,
            "likely_lexical_contamination": likely_lexical_contamination,
            "latent_conflict_underreported": latent_conflict_underreported,
            "suppressed_conflict_disappearance": suppressed_conflict_disappearance,
            "family_fragmentation_hidden": family_fragmentation_hidden,
            "family_conflict_underreported": family_conflict_underreported,
            "cross_area_bridge_underreported": cross_area_bridge_underreported,
            "concentrated_family_conflict_omitted": concentrated_family_conflict_omitted,
            "family_matrix_collapse": family_matrix_collapse,
            "calibration_pathology_masquerading_runtime": calibration_pathology_masquerading_runtime,
            "feedback_trace_missing": feedback_trace_missing,
            "negation_conflict_misalignment": negation_conflict_misalignment,
            "coactive_conflict_overclaimed": coactive_conflict_overclaimed,
            "conflict_confidence_consistency": conflict_confidence_consistency,
            "family_area_alignment_score": family_area_alignment_score,
            "likely_calibration_pathology": likely_cal,
            "session_crossplane_ok": crossplane_ok,
            "latent_vs_overt_mismatch_warn": latent_vs_overt_mismatch_warn,
        }
        per_session_gates = build_release_conflict_gates(session_flags)
        session_flag_rows.append(session_flags)
        per_session.append(
            {
                "session_id": sid,
                "topology_max_segment_contradiction_load": round(g_topo, 6),
                "product_session_mode": mode,
                "crossplane_contradiction_consistency": crossplane_ok,
                "product_underreports_conflict": product_underreports_conflict,
                "dlcr_conflict_misalignment": dlcr_conflict_misalignment,
                "multiscale_conflict_collapse": multiscale_conflict_collapse,
                "verdict_underreports_conflict_reported": under,
                "raw_vs_effective_conflict_gap": round(raw_vs_effective_gap, 6),
                "conflict_confidence_consistency": conflict_confidence_consistency,
                "likely_lexical_contamination": likely_lexical_contamination,
                "likely_concept_ambiguity_overdrive": likely_concept_ambiguity_overdrive,
                "semantic_conflict_reliability": round(sem_rel, 6),
                "conflict_confidence_summary_echo": cfs,
                "recommended_next_action": (
                    "review_contradiction_rows_and_rerun"
                    if product_underreports_conflict
                    or dlcr_conflict_misalignment
                    or likely_lexical_contamination
                    or negation_conflict_misalignment
                    or latent_conflict_underreported
                    else "none"
                ),
                "negation_conflict_misalignment": negation_conflict_misalignment,
                "latent_conflict_underreported": latent_conflict_underreported,
                "coactive_conflict_overclaimed": coactive_conflict_overclaimed,
                "suppressed_conflict_disappearance": suppressed_conflict_disappearance,
                "conflict_mode_consistency": conflict_mode_consistency,
                "family_conflict_underreported": family_conflict_underreported,
                "family_fragmentation_hidden": family_fragmentation_hidden,
                "cross_area_bridge_underreported": cross_area_bridge_underreported,
                "concentrated_family_conflict_omitted": concentrated_family_conflict_omitted,
                "family_matrix_collapse": family_matrix_collapse,
                "family_area_alignment_score": round(family_area_alignment_score, 6),
                "calibration_contradiction_risk": round(likely_cal, 6),
                "likely_runtime_vs_calibration_split": {
                    "likely_runtime_real": round(likely_run, 6),
                    "likely_calibration_pathology": round(likely_cal, 6),
                },
                "persistent_low_conflict_confidence_pairs": persistent_low_conflict_confidence_pairs,
                "feedback_trace_missing": feedback_trace_missing,
                "calibration_pathology_masquerading_runtime": calibration_pathology_masquerading_runtime,
                "recommended_calibration_action": recommended_calibration_action,
                "release_conflict_gates": per_session_gates,
            }
        )

    overall = all(s.get("crossplane_contradiction_consistency") for s in per_session) if per_session else True
    cal_profile, cal_audit = _resolve_calibration_profile(bundle_dir, d20, d00)
    integrity = evaluate_conflict_integrity(session_flag_rows, contradiction_calibration=cal_profile)
    summary = build_conflict_release_summary(integrity)
    contract = validate_contradiction_contract(
        {
            "04_dlcr_full.json": d04,
            "05_sealed_multiscale.json": d05,
            "06_product_analyze.json": d06,
            "09_session_topology.json": d09,
            "20_main_engine_full_context.json": d20,
            "00_manifest.json": _load(bundle_dir / "00_manifest.json"),
        }
    )
    if contract["contract_valid"]:
        contract_recommended_action = "none"
    elif contract["authority_conflicts"]:
        contract_recommended_action = "stop_promotion_and_fix_authority_conflicts"
    elif contract["missing_required_fields"]:
        contract_recommended_action = "fill_required_contradiction_fields_and_reinspect"
    elif contract["deprecated_fields_found"]:
        contract_recommended_action = "remove_deprecated_alias_fields_and_reinspect"
    else:
        contract_recommended_action = "inspect_compatibility_notes"
    ps_detail = (integrity.get("release_conflict_gates") or {}).get("per_session") or []
    for i, row in enumerate(ps_detail):
        if i < len(per_session):
            per_session[i]["session_conflict_integrity_score"] = row.get("conflict_integrity_score")
            per_session[i]["session_promotion_conflict_verdict"] = row.get("promotion_conflict_verdict")
    return {
        "run": "inspect_tfp_bundle_output",
        "bundle_dir": str(bundle_dir),
        "crossplane_contradiction_consistency": overall,
        "conflict_integrity_score": integrity["conflict_integrity_score"],
        "promotion_conflict_verdict": integrity["promotion_conflict_verdict"],
        "promotion_conflict_reasons": integrity["promotion_conflict_reasons"],
        "release_conflict_gates": integrity["release_conflict_gates"],
        "conflict_release_summary": summary,
        "contradiction_contract_spec_version": contract["spec_version"],
        "contradiction_contract_valid": contract["contract_valid"],
        "missing_required_contradiction_fields": contract["missing_required_fields"],
        "deprecated_contradiction_fields_found": contract["deprecated_fields_found"],
        "authority_conflicts": contract["authority_conflicts"],
        "contract_compatibility_notes": contract["compatibility_notes"],
        "contract_missing_required_artifacts": contract["missing_required_artifacts"],
        "contract_recommended_action": contract_recommended_action,
        "sessions": per_session,
        **cal_audit,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Inspect TFP bundle 04/05/06/09 for contradiction coherence.")
    ap.add_argument("--bundle-dir", "-d", type=Path, required=True, help="Output directory from run_tfp_file_pipeline")
    ap.add_argument("--json", action="store_true", help="Print JSON only")
    args = ap.parse_args()
    report = inspect_bundle(args.bundle_dir.resolve())
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
