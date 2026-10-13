# HESPERIA — RAD. Operational anomaly taxonomy for TFP multi-plane bundles (Task 7).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_REGISTRY_PATH = _REPO / "assets" / "config" / "output_anomaly_codes_v1.json"

TAXONOMY_VERSION = "1.0.0"

BLOCKING_CODES = frozenset(
    {
        "A001_NO_ATTRIBUTION",
        "A002_UPSTREAM_NONZERO_DOWNSTREAM_ZERO",
        "A005_SCALE_CONTRACT_VIOLATION",
    }
)


def default_operational_envelope() -> dict[str, Any]:
    """Explicit empty-good envelope (must be present on every artifact root)."""
    return {
        "status": "ok",
        "anomaly_codes": [],
        "severity": "ok",
        "blocking": False,
        "operator_message": "",
        "recommended_next_check": "",
        "taxonomy_version": TAXONOMY_VERSION,
    }


def _core_structural(row: dict[str, Any]) -> dict[str, Any]:
    pl = row.get("payload")
    return pl if isinstance(pl, dict) else row


def assess_structural_row(row: dict[str, Any]) -> list[str]:
    if row.get("_error"):
        return ["A001_NO_ATTRIBUTION"]
    core = _core_structural(row)
    L1 = core.get("L1") or {}
    att = int(L1.get("ATTRIBUTED_TOKENS") or 0)
    fallback = L1.get("CALIBRATION_FALLBACK_USED")
    cal = (core.get("diagnostics") or {}).get("calibration_status") or {}
    l1_fb = cal.get("l1_calibration_fallback")
    if att == 0 and not fallback and not l1_fb:
        return ["A001_NO_ATTRIBUTION"]
    return []


def assess_sealed_session(sess: dict[str, Any]) -> list[str]:
    if sess.get("_error"):
        return ["A002_UPSTREAM_NONZERO_DOWNSTREAM_ZERO"]
    ham = sess.get("hex_activation_map") or {}
    mass = float(ham.get("total_mass") or 0.0)
    if mass <= 0.0:
        return ["A002_UPSTREAM_NONZERO_DOWNSTREAM_ZERO"]
    return []


def assess_analyze_session(sess: dict[str, Any]) -> list[str]:
    if sess.get("_error"):
        return []
    ext = sess.get("extended") or {}
    cov = float(ext.get("attribution_coverage") or 0.0)
    if cov < 0.0 or cov > 1.0 + 1e-9:
        return ["A005_SCALE_CONTRACT_VIOLATION"]
    return []


def cross_plane_codes(
    struct_row: dict[str, Any] | None,
    sealed_sess: dict[str, Any] | None,
    analyze_sess: dict[str, Any] | None,
) -> list[str]:
    if not struct_row or not analyze_sess or analyze_sess.get("_error"):
        return []
    core = _core_structural(struct_row)
    L1 = core.get("L1") or {}
    att = int(L1.get("ATTRIBUTED_TOKENS") or 0)
    fallback = bool(
        L1.get("CALIBRATION_FALLBACK_USED")
        or (core.get("diagnostics") or {}).get("calibration_status", {}).get("l1_calibration_fallback")
    )
    ext = analyze_sess.get("extended") or {}
    cov = float(ext.get("attribution_coverage") or 0.0)
    codes: list[str] = []
    if cov >= 0.9 and att == 0 and not fallback:
        codes.append("A007_CROSS_PLANE_INCONSISTENCY")
    if sealed_sess and not sealed_sess.get("_error"):
        mass = float((sealed_sess.get("hex_activation_map") or {}).get("total_mass") or 0.0)
        if cov >= 0.9 and mass <= 0.0:
            codes.append("A007_CROSS_PLANE_INCONSISTENCY")
    return list(dict.fromkeys(codes))


def codes_to_envelope(
    codes: list[str],
    *,
    operator_message: str = "",
    recommended_next_check: str = "",
) -> dict[str, Any]:
    env = default_operational_envelope()
    if not codes:
        return env
    env["anomaly_codes"] = list(codes)
    blocking = any(c in BLOCKING_CODES for c in codes)
    has_err = any(
        c in ("A001_NO_ATTRIBUTION", "A002_UPSTREAM_NONZERO_DOWNSTREAM_ZERO", "A005_SCALE_CONTRACT_VIOLATION")
        for c in codes
    )
    env["blocking"] = blocking
    env["severity"] = "error" if has_err else "warn" if codes else "ok"
    env["status"] = "failed" if blocking or has_err else "degraded"
    env["operator_message"] = operator_message or "; ".join(codes)
    env["recommended_next_check"] = recommended_next_check or (
        "Re-run bundle after calibration patch; see docs/specs/output_anomaly_taxonomy_v1.md"
    )
    return env


def aggregate_file_envelope(child_envelopes: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge anomaly codes across children; derive status from merged codes."""
    if not child_envelopes:
        return default_operational_envelope()
    all_codes: list[str] = []
    for e in child_envelopes:
        all_codes.extend(e.get("anomaly_codes") or [])
    merged = list(dict.fromkeys(all_codes))
    return codes_to_envelope(merged)


def apply_envelopes_standalone_sealed_analyze(
    session_sealed: list[dict[str, Any]],
    session_analyze: list[dict[str, Any]],
) -> None:
    """When structural batch is skipped, still emit per-row envelopes for sealed/analyze."""
    for se in session_sealed:
        se["operational_envelope"] = codes_to_envelope(assess_sealed_session(se))
    for an in session_analyze:
        an["operational_envelope"] = codes_to_envelope(assess_analyze_session(an))


def apply_session_envelopes(
    *,
    structural_batch: list[dict[str, Any]] | None,
    session_sealed: list[dict[str, Any]],
    session_analyze: list[dict[str, Any]],
) -> None:
    """Mutate rows in place: attach operational_envelope per session where present."""
    by_sealed = {r["session_id"]: r for r in session_sealed if r.get("session_id")}
    by_an = {r["session_id"]: r for r in session_analyze if r.get("session_id")}
    if not structural_batch:
        return
    for row in structural_batch:
        sid = row.get("session_id")
        if not sid:
            continue
        se = by_sealed.get(str(sid))
        an = by_an.get(str(sid))
        c_st = assess_structural_row(row)
        c_se = assess_sealed_session(se) if se else []
        c_an = assess_analyze_session(an) if an else []
        c_x = cross_plane_codes(row, se, an)
        all_c = list(dict.fromkeys([*c_st, *c_se, *c_an, *c_x]))
        row["operational_envelope"] = codes_to_envelope(all_c)
        if se:
            se_c = list(dict.fromkeys([*c_se, *c_x]))
            se["operational_envelope"] = codes_to_envelope(se_c)
        if an:
            an_c = list(dict.fromkeys([*c_an, *c_x]))
            an["operational_envelope"] = codes_to_envelope(an_c)
