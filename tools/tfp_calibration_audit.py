#!/usr/bin/env python3
# HESPERIA — RAD. Cross-plane calibration audit for TFP file pipeline bundle (Task 4).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Load TFP bundle artifacts and emit ``10_calibration_audit.json`` with invariant-path checks.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.engine.output_anomalies import codes_to_envelope, default_operational_envelope

NEAR_EQUAL_DOMINANT_TOLERANCE = 0.015
NEAR_EQUAL_DOMINANT_COUNT = 3
HEX_EFFECT_MIN_L1 = 0.01
FINAL_AREA_COLLAPSE_MAX = 0.9
FINAL_AREA_FLATNESS_ENTROPY = 2.2
SEGMENT_LENGTH_SENSITIVITY_RATIO = 3.0
MAX_CONTRADICTIONS_PER_LEXICAL_HIT = 5.0
# Family/area grain (pipeline writes family share into these fields). Concept-level is diagnostic.
MAX_ZERO_LEX_SHARE = 0.6
MAX_INFERRED_SHARE = 0.6
MIN_HEX_DELTA_L1_HARD = 0.01
MIN_TOP_AREA_CHANGE_HARD = 0.02


def _load(p: Path) -> dict[str, Any] | None:
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _top_keys(d: dict[str, Any], n: int = 8) -> list[str]:
    return sorted(d.keys(), key=lambda k: float(d.get(k) or 0), reverse=True)[:n]


def _entropy(values: dict[str, Any]) -> float:
    probs = [max(0.0, float(v)) for v in values.values()]
    total = sum(probs)
    if total <= 1e-12:
        return 0.0
    h = 0.0
    for p in probs:
        if p <= 0:
            continue
        q = p / total
        h -= q * math.log(q + 1e-15)
    return h


def _l1_delta(a: dict[str, Any], b: dict[str, Any]) -> float:
    keys = sorted(set(a) | set(b))
    return sum(abs(float(a.get(k) or 0.0) - float(b.get(k) or 0.0)) for k in keys)


def _near_equal_dominants(values: dict[str, Any], *, tolerance: float = NEAR_EQUAL_DOMINANT_TOLERANCE) -> int:
    items = sorted((float(v), str(k)) for k, v in values.items())
    if not items:
        return 0
    top = items[-1][0]
    return sum(1 for value, _key in items if abs(top - value) <= tolerance)


def run_audit(bundle_dir: Path) -> dict[str, Any]:
    bundle_dir = bundle_dir.resolve()
    suspects: list[str] = []
    alarms: list[str] = []
    plane_notes: dict[str, Any] = {}

    s01 = _load(bundle_dir / "01_structural_batch.json")
    s02 = _load(bundle_dir / "02_session_tfp_stages.json")
    s04 = _load(bundle_dir / "04_dlcr_full.json")
    s05 = _load(bundle_dir / "05_sealed_multiscale.json")
    s06 = _load(bundle_dir / "06_product_analyze.json")
    s09 = _load(bundle_dir / "09_session_topology.json")
    s13 = _load(bundle_dir / "13_contradiction_reconciliation.json")
    s20 = _load(bundle_dir / "20_main_engine_full_context.json")

    l1_attributed = None
    hex_mass = None
    analyze_cov = None
    stage_final: dict[str, Any] = {}
    stage_raw: dict[str, Any] = {}
    stage_inhibited: dict[str, Any] = {}

    if s01 and s01.get("structural_batch"):
        row = s01["structural_batch"][0]
        core = row.get("payload") if isinstance(row.get("payload"), dict) else row
        L1 = core.get("L1") or {}
        l1_attributed = int(L1.get("ATTRIBUTED_TOKENS") or 0)
        cal = (core.get("diagnostics") or {}).get("calibration_status") or {}
        plane_notes["structural"] = {
            "l1_attributed_tokens": l1_attributed,
            "l1_coverage": float(L1.get("COVERAGE_RATIO") or 0.0),
            "calibration_status": cal,
            "l1_fallback": L1.get("CALIBRATION_FALLBACK_USED"),
        }
        if l1_attributed == 0 and not cal.get("l1_calibration_fallback"):
            suspects.append("structural.L1_zero_without_fallback")

    if s02 and s02.get("session_tfp_stages"):
        st = s02["session_tfp_stages"][0]
        stage_final = st.get("areas_final") or st.get("areas_top") or {}
        stage_raw = st.get("areas_raw") or {}
        stage_inhibited = st.get("areas_inhibited") or {}
        plane_notes["stages"] = {
            "areas_top_keys": _top_keys(stage_final, 6),
            "activation_path_id": st.get("activation_path_id"),
            "config_version": st.get("config_version"),
            "hex_feedback_active": st.get("hex_feedback_active"),
            "areas_raw": stage_raw,
            "areas_inhibited": stage_inhibited,
            "areas_final": stage_final,
        }
        # Matches hesperia/engine/calibration_release_gate.py's own _allowed_operator_ids: that
        # gate already treats "engine_invariant_activation_v2" as a legitimate outcome (session-stage
        # classification via analyze_session()/build_invariant_activation() calls load_engine_runtime_bundle()
        # with no TFP-calibration override parameter, so it structurally can only ever emit that value,
        # never "tfp_invariant_activation_v2"). Chiron, 2026-08-17: this check disagreed with the gate it
        # feeds into (audit_operator_path_not_bypassed reads this alarm list) -- false INVARIANT_PATH_NOT_USED
        # alarm on every TFP session-stage run. Widening to match, not narrowing the gate's own policy.
        if st.get("activation_path_id") not in ("tfp_invariant_activation_v2", "engine_invariant_activation_v2"):
            suspects.append("stages.invariant_path_missing")
            alarms.append("INVARIANT_PATH_NOT_USED")

    if s04 and s04.get("sessions"):
        sess0 = s04["sessions"][0]
        raw_concepts = sess0.get("concept_weights_stabilized") or sess0.get("concept_weights_raw") or {}
        post_hex = sess0.get("concept_weights_post_hex") or sess0.get("concept_weights") or {}
        family_raw = sess0.get("family_activation_raw") or {}
        family_post = sess0.get("family_activation") or {}
        hex_delta = sess0.get("hex_feedback_delta") or {}
        plane_notes["dlcr"] = {
            "concept_weights_raw": raw_concepts,
            "concept_weights_post_hex": post_hex,
            "family_activation_raw": family_raw,
            "family_activation_post_hex": family_post,
            "hex_feedback_delta_l1": round(sum(abs(float(v)) for v in hex_delta.values()), 6),
        }
        if sum(abs(float(v)) for v in hex_delta.values()) <= HEX_EFFECT_MIN_L1:
            suspects.append("dlcr.hex_feedback_negligible")
            alarms.append("HEX_LAYER_EFFECT_NEGLIGIBLE")
        if raw_concepts and post_hex and _l1_delta(raw_concepts, post_hex) <= 1e-9:
            suspects.append("dlcr.pre_post_hex_identical")

    if s05 and s05.get("sessions"):
        sess0 = s05["sessions"][0]
        ham = sess0.get("hex_activation_map") or {}
        hex_mass = float(ham.get("total_mass") or 0.0)
        cl = sess0.get("concept_layer") or {}
        plane_notes["sealed"] = {
            "hex_total_mass": hex_mass,
            "uniform_concept_prior_fallback_used": cl.get("uniform_concept_prior_fallback_used"),
            "hex_upstream_fallback_used": cl.get("hex_upstream_fallback_used"),
        }
        if hex_mass <= 0.0:
            suspects.append("sealed.hex_total_mass_zero")
            alarms.append("IMPOSSIBLE_STATE:hex_mass_zero_with_running_pipeline")

    if s06 and s06.get("sessions"):
        row = s06["sessions"][0]
        ext = row.get("extended") or {}
        analyze_cov = float(ext.get("attribution_coverage") or 0.0)
        plane_notes["analyze"] = {
            "attribution_coverage": analyze_cov,
            "matched_tokens": ext.get("matched_tokens"),
            "total_tokens": ext.get("total_tokens"),
        }

    if s09 and s09.get("sessions"):
        topo = (s09["sessions"][0] or {}).get("session_topology") or {}
        raw_curves = topo.get("area_curves_raw") or {}
        stable_curves = topo.get("area_curves_stable") or topo.get("area_curves") or {}
        cmeta = topo.get("curve_projection_meta") or {}
        plane_notes["topology"] = {
            "area_curves_raw": raw_curves,
            "area_curves_stable": stable_curves,
            "temporal_momentum": cmeta.get("temporal_momentum"),
        }
        if not cmeta.get("temporal_momentum"):
            suspects.append("topology.temporal_momentum_missing")
            alarms.append("TEMPORAL_MOMENTUM_METADATA_MISSING")

    if s13 and s13.get("sessions"):
        rec = (s13.get("sessions") or [{}])[0] if isinstance(s13.get("sessions"), list) else {}
        if isinstance(rec, dict):
            lexical = rec.get("lexical_support") or {}
            ratio = float(lexical.get("contradictions_per_accepted_lexical_hit") or 0.0)
            zero_lex_share = float(lexical.get("zero_lexical_evidence_share") or 0.0)
            inferred_share = float(lexical.get("inferred_share") or 0.0)
            plane_notes["contradiction_authority"] = {
                "canonical_source": rec.get("canonical_source"),
                "contradictions_direct_triz": rec.get("contradictions_direct_triz"),
                "contradictions_topology_derived": rec.get("contradictions_topology_derived"),
                "delta_count": rec.get("delta_count"),
                "lexical_hits_accepted": lexical.get("lexical_hits_accepted"),
                "contradictions_per_accepted_lexical_hit": ratio,
                "grounding_granularity": lexical.get("grounding_granularity") or "family",
                "zero_lexical_evidence_share": zero_lex_share,
                "inferred_share": inferred_share,
                "zero_lexical_evidence_share_concept": lexical.get("zero_lexical_evidence_share_concept"),
                "zero_area_lexical_evidence_share": lexical.get("zero_area_lexical_evidence_share"),
                "segment_entropy": lexical.get("segment_entropy"),
            }
            if rec.get("canonical_source") != "12_topology_derived_contradictions":
                suspects.append("contradictions.canonical_source_mismatch")
                alarms.append("CANONICAL_CONTRADICTION_SOURCE_MISMATCH")
            if ratio > MAX_CONTRADICTIONS_PER_LEXICAL_HIT:
                suspects.append("contradictions.probable_overproduction")
                alarms.append("CONTRADICTION_OVERPRODUCTION")
            if zero_lex_share > MAX_ZERO_LEX_SHARE:
                suspects.append("contradictions.zero_lex_share_high")
                alarms.append("CONTRADICTION_ZERO_LEX_EVIDENCE_HIGH")
            if inferred_share > MAX_INFERRED_SHARE:
                suspects.append("contradictions.inferred_share_high")
                alarms.append("CONTRADICTION_INFERRED_SHARE_HIGH")

    if s20 and s20.get("sessions"):
        srow = (s20.get("sessions") or [{}])[0] if isinstance(s20.get("sessions"), list) else {}
        if isinstance(srow, dict):
            effect = srow.get("invariant_path_effect") or {}
            plane_notes["invariant_path_effect"] = {
                "hex_contribution_delta_l1": effect.get("hex_contribution_delta_l1"),
                "top_area_before": effect.get("top_area_before"),
                "top_area_after": effect.get("top_area_after"),
                "top_area_change_magnitude": effect.get("top_area_change_magnitude"),
                "rank_changes": effect.get("rank_changes"),
            }
            if float(effect.get("hex_contribution_delta_l1") or 0.0) <= HEX_EFFECT_MIN_L1:
                suspects.append("invariant.hex_effect_negligible")
                alarms.append("INVARIANT_PATH_EFFECT_NEGLIGIBLE")
            if float(effect.get("top_area_change_magnitude") or 0.0) <= 1e-6:
                suspects.append("invariant.top_area_unchanged")
            if float(effect.get("hex_contribution_delta_l1") or 0.0) < MIN_HEX_DELTA_L1_HARD:
                suspects.append("invariant.hex_effect_below_hard_min")
            if float(effect.get("top_area_change_magnitude") or 0.0) < MIN_TOP_AREA_CHANGE_HARD:
                suspects.append("invariant.top_area_change_below_hard_min")

    score = 1.0
    if l1_attributed == 0 and (analyze_cov or 0) >= 0.99:
        score -= 0.35
        alarms.append("HIGH_analyze_coverage_with_zero_L1_attributed")
    if hex_mass is not None and hex_mass <= 0 and (analyze_cov or 0) >= 0.5:
        score -= 0.4
    if stage_final:
        entropy = _entropy(stage_final)
        top_mass = max(float(v) for v in stage_final.values()) if stage_final else 0.0
        plane_notes.setdefault("stages", {})["final_area_entropy"] = round(entropy, 6)
        if _near_equal_dominants(stage_final) >= NEAR_EQUAL_DOMINANT_COUNT:
            suspects.append("stages.near_equal_dominants")
            alarms.append("TOO_MANY_NEAR_EQUAL_DOMINANT_AREAS")
            score -= 0.15
        if top_mass >= FINAL_AREA_COLLAPSE_MAX:
            suspects.append("stages.extreme_collapse")
            alarms.append("FINAL_AREA_DISTRIBUTION_COLLAPSED")
            score -= 0.1
        if entropy >= FINAL_AREA_FLATNESS_ENTROPY:
            suspects.append("stages.persistent_flatness")
            alarms.append("FINAL_AREA_DISTRIBUTION_TOO_FLAT")
            score -= 0.1
        if stage_raw and stage_inhibited:
            inh_delta = _l1_delta(stage_raw, stage_inhibited)
            plane_notes.setdefault("stages", {})["raw_to_inhibited_l1"] = round(inh_delta, 6)
            if inh_delta <= 1e-9:
                suspects.append("stages.inhibition_inactive")
                alarms.append("AREA_INHIBITION_NEGLIGIBLE")
                score -= 0.15
        if abs(sum(float(v) for v in stage_final.values()) - 1.0) > 0.05 and sum(
            float(v) for v in stage_final.values()
        ) > 0.0:
            suspects.append("stages.final_area_sum_not_one")
            alarms.append("FINAL_AREA_VECTOR_NOT_NORMALIZED")
            score -= 0.2

    if plane_notes.get("dlcr"):
        raw_concepts = plane_notes["dlcr"].get("concept_weights_raw") or {}
        post_hex = plane_notes["dlcr"].get("concept_weights_post_hex") or {}
        if raw_concepts and post_hex:
            max_raw = max(float(v) for v in raw_concepts.values())
            max_post = max(float(v) for v in post_hex.values())
            if max_post > 0 and max_raw / max_post >= SEGMENT_LENGTH_SENSITIVITY_RATIO:
                suspects.append("dlcr.segment_length_sensitivity_high")
                alarms.append("EXTREME_SEGMENT_LENGTH_SENSITIVITY")
                score -= 0.1

    if plane_notes.get("topology"):
        raw_curves = plane_notes["topology"].get("area_curves_raw") or {}
        stable_curves = plane_notes["topology"].get("area_curves_stable") or {}
        if raw_curves and stable_curves:
            deltas = []
            for key in sorted(set(raw_curves) | set(stable_curves)):
                raw_series = raw_curves.get(key) or []
                stable_series = stable_curves.get(key) or []
                n = min(len(raw_series), len(stable_series))
                deltas.append(sum(abs(float(raw_series[i]) - float(stable_series[i])) for i in range(n)))
            plane_notes["topology"]["raw_to_stable_curve_l1"] = round(sum(deltas), 6)

    score = max(0.0, min(1.0, score))

    ranking = ["analyze", "stages", "topology", "kme", "sealed", "structural"]
    if plane_notes.get("structural", {}).get("l1_attributed_tokens", 0) > 0:
        ranking = ["structural", "stages", "dlcr", "sealed", "analyze", "topology", "kme"]

    audit_codes: list[str] = []
    if alarms:
        audit_codes.append("A007_CROSS_PLANE_INCONSISTENCY")
    if "sealed.hex_total_mass_zero" in suspects:
        audit_codes.append("A002_UPSTREAM_NONZERO_DOWNSTREAM_ZERO")
    if "stages.invariant_path_missing" in suspects:
        audit_codes.append("A009_INVARIANT_PATH_BYPASSED")
    if "contradictions.probable_overproduction" in suspects:
        audit_codes.append("A010_CONTRADICTION_OVERPRODUCTION")
    if "contradictions.zero_lex_share_high" in suspects or "contradictions.inferred_share_high" in suspects:
        audit_codes.append("A011_CONTRADICTION_GROUNDING_WEAK")

    return {
        "run": "tfp_calibration_audit_v2",
        "bundle_dir": str(bundle_dir),
        "consistency_score": round(score, 4),
        "plane_reliability_ranking": ranking,
        "suspect_fields": suspects,
        "alarms": alarms,
        "likely_breakpoint_stage": "invariant_activation"
        if "stages.invariant_path_missing" in suspects
        else "hex_microphysics_line_search"
        if "sealed.hex_total_mass_zero" in suspects
        else None,
        "plane_notes": plane_notes,
        "registry_hint": "assets/config/output_metric_registry_v1.json",
        "operational_envelope": codes_to_envelope(list(dict.fromkeys(audit_codes)))
        if audit_codes
        else default_operational_envelope(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit 10_calibration_audit.json for a TFP bundle directory.")
    ap.add_argument("--bundle-dir", type=Path, required=True, help="Directory with 01_*.json … 09_*.json")
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: bundle-dir/10_calibration_audit.json)",
    )
    args = ap.parse_args()
    out = args.out or (args.bundle_dir.resolve() / "10_calibration_audit.json")
    body = run_audit(args.bundle_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
