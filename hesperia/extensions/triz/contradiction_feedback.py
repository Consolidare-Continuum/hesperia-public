from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from core.math.basic_stats import clamp01 as _clamp01

_EPS = 1e-15


def score_lexical_calibration_risk(
    lexical_output: dict[str, Any] | None,
    contradiction_rows: list[dict[str, Any]] | None,
    uncertainty_package: dict[str, Any] | None,
    *,
    top_k: int = 20,
    feedback_cal: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    lexical_output = lexical_output or {}
    rows = contradiction_rows or []
    unc = uncertainty_package or {}
    span_rows = lexical_output.get("span_resolutions") or []
    winners = [str(r.get("winning_concept_id")) for r in span_rows if isinstance(r, dict) and r.get("winning_concept_id")]
    total = len(winners) or 1
    concept_freq = Counter(winners)
    concept_conflict: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        pair = row.get("pair")
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        burden = float(row.get("raw_contradiction_score") or row.get("score") or 0.0)
        concept_conflict[str(pair[0])] += burden
        concept_conflict[str(pair[1])] += burden

    fc = feedback_cal or {}
    w_tok = float(fc.get("token_risk_influence", 1.0))
    w_rec = float(fc.get("recurrence_influence", 1.0))
    fuzzy = float(unc.get("fuzzy_link_ratio") or 0.0)
    amb = float(unc.get("ambiguous_concept_share") or 0.0)
    out: list[dict[str, Any]] = []
    for concept_id, cnt in concept_freq.items():
        recurrence = cnt / total
        conflict = _clamp01(concept_conflict.get(concept_id, 0.0))
        risk = _clamp01(
            0.45 * conflict * w_tok
            + 0.25 * recurrence * w_rec
            + 0.18 * fuzzy
            + 0.12 * amb
        )
        out.append(
            {
                "token": concept_id,
                "contradiction_burden": round(conflict, 6),
                "uncertainty_burden": round(_clamp01(0.6 * fuzzy + 0.4 * amb), 6),
                "calibration_risk": round(risk, 6),
                "risk_components": {
                    "fuzzy_dependence": round(fuzzy, 6),
                    "ambiguity": round(amb, 6),
                    "conflict_recurrence": round(recurrence, 6),
                },
            }
        )
    out.sort(key=lambda r: (-float(r["calibration_risk"]), str(r["token"])))
    return out[: max(0, int(top_k))]


def score_concept_calibration_risk(
    contradiction_rows: list[dict[str, Any]] | None,
    uncertainty_package: dict[str, Any] | None,
    activation: dict[str, Any] | None,
    *,
    top_k: int = 20,
    feedback_cal: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows = contradiction_rows or []
    unc = uncertainty_package or {}
    act = activation or {}
    participation: defaultdict[str, float] = defaultdict(float)
    recurrence: Counter[str] = Counter()
    for row in rows:
        pair = row.get("pair")
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        raw = float(row.get("raw_contradiction_score") or row.get("score") or 0.0)
        for c in (str(pair[0]), str(pair[1])):
            participation[c] += raw
            recurrence[c] += 1
    fc = feedback_cal or {}
    w_con = float(fc.get("concept_risk_influence", 1.0))
    w_rec = float(fc.get("recurrence_influence", 1.0))
    weak = float(unc.get("weak_concept_share") or 0.0)
    amb = float(unc.get("ambiguous_concept_share") or 0.0)
    frag = float(((act.get("family_fragmentation_summary") or {}).get("global_family_fragmentation") or 0.0))
    out: list[dict[str, Any]] = []
    max_rec = max(recurrence.values()) if recurrence else 1
    for concept_id, raw in sorted(participation.items()):
        rec = recurrence[concept_id] / max_rec
        support_instability = _clamp01(0.5 * weak + 0.3 * amb + 0.2 * frag)
        risk = _clamp01(
            0.5 * _clamp01(raw) * w_con + 0.25 * rec * w_rec + 0.25 * support_instability
        )
        out.append(
            {
                "concept": concept_id,
                "contradiction_burden": round(_clamp01(raw), 6),
                "support_instability": round(support_instability, 6),
                "calibration_risk": round(risk, 6),
            }
        )
    out.sort(key=lambda r: (-float(r["calibration_risk"]), str(r["concept"])))
    return out[: max(0, int(top_k))]


def score_pair_calibration_risk(
    contradiction_rows: list[dict[str, Any]] | None,
    uncertainty_package: dict[str, Any] | None,
    *,
    top_k: int = 20,
    feedback_cal: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows = contradiction_rows or []
    unc = uncertainty_package or {}
    fc = feedback_cal or {}
    w_pair = float(fc.get("pair_risk_influence", 1.0))
    w_rec = float(fc.get("recurrence_influence", 1.0))
    fuzzy = float(unc.get("fuzzy_link_ratio") or 0.0)
    low_conf: defaultdict[tuple[str, str], float] = defaultdict(float)
    raw_sum: defaultdict[tuple[str, str], float] = defaultdict(float)
    eff_sum: defaultdict[tuple[str, str], float] = defaultdict(float)
    rec: Counter[tuple[str, str]] = Counter()
    for row in rows:
        pair = row.get("pair")
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        a = str(pair[0])
        b = str(pair[1])
        key = (a, b) if a <= b else (b, a)
        raw = float(row.get("raw_contradiction_score") or row.get("score") or 0.0)
        eff = float(row.get("effective_score") or row.get("effective_activation_score") or raw)
        conf = float(row.get("confidence") or 1.0)
        raw_sum[key] += raw
        eff_sum[key] += eff
        rec[key] += 1
        if conf < 0.45:
            low_conf[key] += 1.0
    max_rec = max(rec.values()) if rec else 1
    out: list[dict[str, Any]] = []
    for key in sorted(raw_sum):
        raw = _clamp01(raw_sum[key])
        eff = _clamp01(eff_sum[key])
        recurrence = rec[key] / max_rec
        contamination = _clamp01((raw - eff) + 0.25 * fuzzy + 0.2 * (low_conf[key] / max(1, rec[key])))
        risk = _clamp01(
            0.45 * contamination * w_pair + 0.3 * recurrence * w_rec + 0.25 * (1.0 - eff)
        )
        out.append(
            {
                "pair": [key[0], key[1]],
                "raw_conflict": round(raw, 6),
                "effective_conflict": round(eff, 6),
                "pair_recurrence": round(recurrence, 6),
                "calibration_risk": round(risk, 6),
            }
        )
    out.sort(key=lambda r: (-float(r["calibration_risk"]), str(r["pair"])))
    return out[: max(0, int(top_k))]


def build_contradiction_feedback_signals(
    *,
    contradiction_rows: list[dict[str, Any]] | None,
    uncertainty_package: dict[str, Any] | None,
    activation: dict[str, Any] | None = None,
    lexical_output: dict[str, Any] | None = None,
    top_k: int = 20,
    contradiction_calibration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = contradiction_rows or []
    fb = dict((contradiction_calibration or {}).get("feedback") or {})
    lexical_top = score_lexical_calibration_risk(
        lexical_output, rows, uncertainty_package, top_k=top_k, feedback_cal=fb
    )
    concept_top = score_concept_calibration_risk(
        rows, uncertainty_package, activation, top_k=top_k, feedback_cal=fb
    )
    pair_top = score_pair_calibration_risk(rows, uncertainty_package, top_k=top_k, feedback_cal=fb)
    fam_summary = (activation or {}).get("family_fragmentation_summary") or {}
    high_lex = sum(1 for r in lexical_top if float(r.get("calibration_risk") or 0.0) >= 0.6)
    high_con = sum(1 for r in concept_top if float(r.get("calibration_risk") or 0.0) >= 0.6)
    high_pair = sum(1 for r in pair_top if float(r.get("calibration_risk") or 0.0) >= 0.6)
    nlex = max(1, len(lexical_top))
    ncon = max(1, len(concept_top))
    npair = max(1, len(pair_top))
    w_c = float(fb.get("concept_risk_influence", 1.0))
    w_p = float(fb.get("pair_risk_influence", 1.0))
    w_l = float(fb.get("token_risk_influence", 1.0))
    calibration_risk = _clamp01(
        0.4 * w_c * (sum(float(r.get("calibration_risk") or 0.0) for r in concept_top) / ncon)
        + 0.35 * w_p * (sum(float(r.get("calibration_risk") or 0.0) for r in pair_top) / npair)
        + 0.25 * w_l * (sum(float(r.get("calibration_risk") or 0.0) for r in lexical_top) / nlex)
    )
    likely_cal = _clamp01(0.55 * calibration_risk + 0.25 * float(uncertainty_package.get("lexical_uncertainty") if uncertainty_package else 0.0) + 0.2 * float(uncertainty_package.get("concept_uncertainty") if uncertainty_package else 0.0))
    likely_runtime = _clamp01(1.0 - likely_cal)
    return {
        "lexical_feedback": {
            "top_risky_tokens": lexical_top,
            "mean_lexical_calibration_risk": round(sum(float(r.get("calibration_risk") or 0.0) for r in lexical_top) / nlex, 6),
            "high_risk_token_share": round(high_lex / nlex, 6),
        },
        "concept_feedback": {
            "top_risky_concepts": concept_top,
            "mean_concept_calibration_risk": round(sum(float(r.get("calibration_risk") or 0.0) for r in concept_top) / ncon, 6),
            "high_risk_concept_share": round(high_con / ncon, 6),
        },
        "pair_feedback": {
            "top_risky_pairs": pair_top,
            "mean_pair_calibration_risk": round(sum(float(r.get("calibration_risk") or 0.0) for r in pair_top) / npair, 6),
            "high_risk_pair_share": round(high_pair / npair, 6),
        },
        "family_feedback": {
            "family_fragmentation_summary": fam_summary,
            "top_risky_families": list(fam_summary.get("dominant_conflict_families") or []),
        },
        "global_feedback_summary": {
            "calibration_contradiction_risk": round(calibration_risk, 6),
            "runtime_vs_calibration_conflict_split": {
                "likely_runtime_real": round(likely_runtime, 6),
                "likely_calibration_pathology": round(likely_cal, 6),
            },
            "high_risk_token_share": round(high_lex / nlex, 6),
            "high_risk_concept_share": round(high_con / ncon, 6),
            "high_risk_pair_share": round(high_pair / npair, 6),
        },
    }
