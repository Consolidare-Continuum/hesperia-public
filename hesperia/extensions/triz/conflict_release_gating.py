# HESPERIA — Contradiction integrity release gating (v0.5.8 task9).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.
"""Evaluate contradiction *handling* integrity for promotion — not mere presence of conflict."""

from __future__ import annotations

from typing import Any, Literal

GateStatus = Literal["PASS", "WARN", "FAIL"]
PromotionVerdict = Literal["PASS", "QUALIFIED_PASS", "FAIL"]

_GATE_ORDER = {"FAIL": 3, "WARN": 2, "PASS": 1}


def _worst(a: GateStatus, b: GateStatus) -> GateStatus:
    return a if _GATE_ORDER[a] >= _GATE_ORDER[b] else b


def build_release_conflict_gates(flags: dict[str, Any]) -> dict[str, Any]:
    """
    Structured gate states from per-session inspector flags (integrity, not raw conflict).

    `flags` expects keys produced by inspect_tfp_bundle (see inspect loop).
    """
    g_topo = float(flags.get("topology_max_segment_contradiction_load") or 0.0)
    mode = str(flags.get("product_session_mode") or "")
    eff_l = float(flags.get("effective_contradiction_load") or 0.0)
    raw_l = float(flags.get("raw_contradiction_load") or 0.0)
    sem_rel = float(flags.get("semantic_conflict_reliability") or 0.0)
    under = bool(flags.get("verdict_underreports_conflict_reported"))
    product_under = bool(flags.get("product_underreports_conflict"))
    dlcr_mis = bool(flags.get("dlcr_conflict_misalignment"))
    ms_collapse = bool(flags.get("multiscale_conflict_collapse"))
    lex_contam = bool(flags.get("likely_lexical_contamination"))
    latent_under = bool(flags.get("latent_conflict_underreported"))
    suppressed_dis = bool(flags.get("suppressed_conflict_disappearance"))
    fam_hidden = bool(flags.get("family_fragmentation_hidden"))
    fam_under = bool(flags.get("family_conflict_underreported"))
    bridge_under = bool(flags.get("cross_area_bridge_underreported"))
    fam_omit = bool(flags.get("concentrated_family_conflict_omitted"))
    fam_matrix = bool(flags.get("family_matrix_collapse"))
    cal_masq = bool(flags.get("calibration_pathology_masquerading_runtime"))
    feedback_miss = bool(flags.get("feedback_trace_missing"))
    neg_mis = bool(flags.get("negation_conflict_misalignment"))
    co_over = bool(flags.get("coactive_conflict_overclaimed"))
    conf_inconsist = bool(flags.get("conflict_confidence_consistency") is False)

    # 6.1 Contradiction visibility — downstream must not fake coherence when upstream conflict is meaningful.
    vis_fail = product_under or (
        g_topo > 0.45 and mode == "coherent" and not under and eff_l > 0.25
    )
    vis_warn = (g_topo > 0.35 or eff_l > 0.35) and mode == "coherent" and not under and not vis_fail
    if vis_fail:
        contradiction_visibility_gate: dict[str, Any] = {
            "status": "FAIL",
            "score": 0.18,
            "reason": "Contradiction visible upstream/topology but product layer signals false coherence or under-reporting.",
        }
    elif vis_warn:
        contradiction_visibility_gate = {
            "status": "WARN",
            "score": 0.68,
            "reason": "Contradiction partially visible; product coherence may be under-qualified for downstream promotion.",
        }
    else:
        contradiction_visibility_gate = {
            "status": "PASS",
            "score": 1.0,
            "reason": "Contradiction visibility across activation/product/topology is aligned enough for gating.",
        }

    # 6.2 Cross-plane alignment — one plane must not erase another without trace.
    cross_fail = (
        dlcr_mis
        or ms_collapse
        or product_under
        or neg_mis
        or latent_under
        or co_over
        or suppressed_dis
        or (lex_contam and sem_rel > 0.75 and mode == "coherent")
    )
    session_ok = bool(flags.get("session_crossplane_ok", True))
    cross_warn = (not cross_fail) and ((not session_ok) or conf_inconsist)
    if cross_fail:
        crossplane_alignment_gate = {
            "status": "FAIL",
            "score": 0.2,
            "reason": "DLCR, multiscale, product, or topology layers disagree on contradiction handling (misalignment or collapse).",
        }
    elif cross_warn:
        crossplane_alignment_gate = {
            "status": "WARN",
            "score": 0.65,
            "reason": "Minor cross-plane tension or confidence inconsistency; review before wide promotion.",
        }
    else:
        crossplane_alignment_gate = {
            "status": "PASS",
            "score": 1.0,
            "reason": "Cross-plane contradiction signals are mutually consistent.",
        }

    # 6.3 Latent conflict — inhibited/negated load must not disappear from verdict.
    latent_fail = latent_under or suppressed_dis
    latent_warn = bool(flags.get("latent_vs_overt_mismatch_warn"))
    if latent_fail:
        latent_conflict_gate = {
            "status": "FAIL",
            "score": 0.2,
            "reason": "Latent or suppressed contradiction is mis-reported relative to activation/product.",
        }
    elif latent_warn:
        latent_conflict_gate = {
            "status": "WARN",
            "score": 0.7,
            "reason": "Latent/overt tension present; ensure product narrative reflects it.",
        }
    else:
        latent_conflict_gate = {
            "status": "PASS",
            "score": 1.0,
            "reason": "Latent contradiction handling is visible where expected.",
        }

    # 6.4 Family conflict — fragmentation/bridge must not be smoothed away by area/product.
    fam_fail = fam_hidden or fam_under or bridge_under or fam_omit or fam_matrix
    fam_warn = float(flags.get("family_area_alignment_score") or 1.0) < 0.55 and not fam_fail
    if fam_fail:
        family_conflict_gate = {
            "status": "FAIL",
            "score": 0.22,
            "reason": "Family-level conflict is strong but area/product layers conceal or omit it.",
        }
    elif fam_warn:
        family_conflict_gate = {
            "status": "WARN",
            "score": 0.66,
            "reason": "Family vs area alignment is weak; check smoothing before promotion.",
        }
    else:
        family_conflict_gate = {
            "status": "PASS",
            "score": 1.0,
            "reason": "Family fragmentation and bridge signals are reflected downstream.",
        }

    # 6.5 Contamination honesty — raw vs effective + uncertainty burden must be honest.
    contam_fail = conf_inconsist or (lex_contam and mode == "coherent" and sem_rel > 0.72 and eff_l > 0.35)
    contam_warn = (raw_l > 0.5 and eff_l < 0.28 and sem_rel > 0.65) and not contam_fail
    if contam_fail:
        contamination_honesty_gate = {
            "status": "FAIL",
            "score": 0.25,
            "reason": "Contaminated or ambiguous contradiction may be presented as clean semantic conflict.",
        }
    elif contam_warn:
        contamination_honesty_gate = {
            "status": "WARN",
            "score": 0.7,
            "reason": "Large raw/effective gap or lexical burden; qualify release notes.",
        }
    else:
        contamination_honesty_gate = {
            "status": "PASS",
            "score": 1.0,
            "reason": "Raw/effective and confidence signals are honest relative to product mode.",
        }

    # 6.6 Runtime vs calibration — pathology must not masquerade as runtime without feedback.
    split_fail = cal_masq or (feedback_miss and float(flags.get("likely_calibration_pathology") or 0.0) > 0.42)
    split_warn = float(flags.get("likely_calibration_pathology") or 0.0) > 0.32 and not split_fail
    if split_fail:
        runtime_vs_calibration_split_gate = {
            "status": "FAIL",
            "score": 0.2,
            "reason": "Calibration pathology likely but feedback/qualification traces are missing or mislabeled as runtime.",
        }
    elif split_warn:
        runtime_vs_calibration_split_gate = {
            "status": "WARN",
            "score": 0.68,
            "reason": "Elevated calibration-pathology estimate; ensure calibration actions are recorded.",
        }
    else:
        runtime_vs_calibration_split_gate = {
            "status": "PASS",
            "score": 1.0,
            "reason": "Runtime vs calibration split is coherent with exported feedback.",
        }

    return {
        "contradiction_visibility_gate": contradiction_visibility_gate,
        "crossplane_alignment_gate": crossplane_alignment_gate,
        "latent_conflict_gate": latent_conflict_gate,
        "family_conflict_gate": family_conflict_gate,
        "contamination_honesty_gate": contamination_honesty_gate,
        "runtime_vs_calibration_split_gate": runtime_vs_calibration_split_gate,
    }


def _session_gate_score(gates: dict[str, Any]) -> float:
    parts = [
        float(gates[k]["score"])
        for k in (
            "contradiction_visibility_gate",
            "crossplane_alignment_gate",
            "latent_conflict_gate",
            "family_conflict_gate",
            "contamination_honesty_gate",
            "runtime_vs_calibration_split_gate",
        )
    ]
    return sum(parts) / max(len(parts), 1)


_PV_ORDER = {"FAIL": 3, "QUALIFIED_PASS": 2, "PASS": 1}


def _promo_worse(a: PromotionVerdict, b: PromotionVerdict) -> PromotionVerdict:
    return a if _PV_ORDER[a] >= _PV_ORDER[b] else b


def _verdict_from_gates(gates: dict[str, Any]) -> PromotionVerdict:
    statuses = [gates[k]["status"] for k in gates if k.endswith("_gate")]
    if any(s == "FAIL" for s in statuses):
        return "FAIL"
    if any(s == "WARN" for s in statuses):
        return "QUALIFIED_PASS"
    return "PASS"


def _reasons_from_gates(gates: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for name, g in gates.items():
        if not name.endswith("_gate"):
            continue
        st = g.get("status")
        if st and st != "PASS":
            out.append(f"{name}:{st}:{g.get('reason', '')}")
    return out


_GATE_NAMES = (
    "contradiction_visibility_gate",
    "crossplane_alignment_gate",
    "latent_conflict_gate",
    "family_conflict_gate",
    "contamination_honesty_gate",
    "runtime_vs_calibration_split_gate",
)


def _verdict_from_release_thresholds(bundle_score: float, rg: dict[str, Any]) -> PromotionVerdict:
    pt = float(rg.get("pass_threshold", 0.85))
    qpt = float(rg.get("qualified_pass_threshold", 0.65))
    if bundle_score >= pt:
        return "PASS"
    if bundle_score >= qpt:
        return "QUALIFIED_PASS"
    return "FAIL"


def evaluate_conflict_integrity(
    session_flag_rows: list[dict[str, Any]],
    *,
    contradiction_calibration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Aggregate per-session inspector flag dicts into bundle-level promotion fields.

    `session_flag_rows`: list of dicts including `session_id` and all keys expected by `build_release_conflict_gates`.

    When ``contradiction_calibration`` includes ``release_gating`` thresholds, the bundle-level
    ``promotion_conflict_verdict`` is the worse of (gate-derived verdict, score-threshold verdict).
    """
    per_session: list[dict[str, Any]] = []

    for row in session_flag_rows:
        sid = str(row.get("session_id") or "")
        gates = build_release_conflict_gates(row)
        s_score = _session_gate_score(gates)
        pv = _verdict_from_gates(gates)
        per_session.append(
            {
                "session_id": sid,
                "conflict_integrity_score": round(s_score, 6),
                "promotion_conflict_verdict": pv,
                "release_conflict_gates": gates,
                "promotion_conflict_reasons": _reasons_from_gates(gates),
            }
        )

    aggregate: dict[str, Any] = {}
    for gname in _GATE_NAMES:
        st: GateStatus = "PASS"
        sc = 1.0
        reason = ""
        for p in per_session:
            g = p["release_conflict_gates"][gname]
            gst: GateStatus = g["status"]  # type: ignore[assignment]
            if _GATE_ORDER[gst] > _GATE_ORDER[st]:
                st = gst
                reason = str(g.get("reason") or "")
            sc = min(sc, float(g.get("score") or 0.0))
        aggregate[gname] = {"status": st, "score": sc, "reason": reason}

    scores = [p["conflict_integrity_score"] for p in per_session] or [1.0]
    bundle_score = min(scores)
    verdicts = [p["promotion_conflict_verdict"] for p in per_session] or ["PASS"]
    if any(v == "FAIL" for v in verdicts):
        promo = "FAIL"
    elif any(v == "QUALIFIED_PASS" for v in verdicts):
        promo = "QUALIFIED_PASS"
    else:
        promo = "PASS"

    rg = dict((contradiction_calibration or {}).get("release_gating") or {})
    if rg and contradiction_calibration is not None:
        promo = _promo_worse(promo, _verdict_from_release_thresholds(float(bundle_score), rg))

    reasons: list[str] = []
    for p in per_session:
        for r in p.get("promotion_conflict_reasons") or []:
            tagged = f"{p.get('session_id')}:{r}"
            if tagged not in reasons:
                reasons.append(tagged)

    out: dict[str, Any] = {
        "conflict_integrity_score": round(bundle_score, 6),
        "promotion_conflict_verdict": promo,
        "promotion_conflict_reasons": reasons,
        "release_conflict_gates": {
            "per_session": per_session,
            "aggregate": aggregate,
        },
    }
    if rg:
        out["release_gating_threshold_verdict"] = _verdict_from_release_thresholds(float(bundle_score), rg)
    return out


def compute_product_release_conflict_readiness(
    contradiction_package: dict[str, Any],
    *,
    session_mode: str,
    verdict_conflict_alignment: dict[str, Any],
    semantic_conflict_reliability: float,
    conflict_confidence_consistency: bool,
) -> dict[str, Any]:
    """
    Product-layer-only readiness (06). Inspector bundle inspect remains authoritative for promotion.
    """
    eff_l = float(contradiction_package.get("effective_contradiction_load") or contradiction_package.get("global_contradiction_load") or 0.0)
    raw_l = float(contradiction_package.get("raw_contradiction_load") or eff_l)
    split = contradiction_package.get("runtime_vs_calibration_conflict_split") or {}
    likely_cal = float(split.get("likely_calibration_pathology") or 0.0)
    has_feedback = bool(
        contradiction_package.get("feedback_summary")
        or contradiction_package.get("top_risky_concepts")
        or contradiction_package.get("top_risky_pairs")
    )
    under = bool((verdict_conflict_alignment or {}).get("verdict_underreports_conflict"))
    score = 1.0
    if under and eff_l > 0.38:
        score -= 0.28
    if raw_l - eff_l > 0.35 and session_mode == "coherent":
        score -= 0.22
    if not conflict_confidence_consistency:
        score -= 0.2
    if likely_cal > 0.5 and not has_feedback:
        score -= 0.25
    score = max(0.0, min(1.0, score))
    if score < 0.42:
        verdict: PromotionVerdict = "FAIL"
    elif score < 0.78:
        verdict = "QUALIFIED_PASS"
    else:
        verdict = "PASS"
    return {
        "promotion_conflict_verdict": verdict,
        "conflict_integrity_score": round(score, 6),
        "product_layer_only": True,
        "authoritative_gating": "tools/inspect_tfp_bundle_output.py (bundle inspect artifact)",
    }


def build_conflict_release_summary(integrity: dict[str, Any]) -> dict[str, Any]:
    """Compact bundle/manifest payload."""
    agg = (integrity.get("release_conflict_gates") or {}).get("aggregate") or {}
    failed = [k for k, g in agg.items() if isinstance(g, dict) and g.get("status") == "FAIL"]
    warning = [k for k, g in agg.items() if isinstance(g, dict) and g.get("status") == "WARN"]
    return {
        "promotion_conflict_verdict": integrity.get("promotion_conflict_verdict"),
        "conflict_integrity_score": integrity.get("conflict_integrity_score"),
        "failed_gates": failed,
        "warning_gates": warning,
    }
