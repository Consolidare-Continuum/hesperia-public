# HESPERIA — RAD. Release gate for engine calibration bundles (Task 10).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.engine.output_anomalies import aggregate_file_envelope, codes_to_envelope, default_operational_envelope

_LEGACY_PROFILE_ALIAS = {
    "research_allow_degraded": "exploratory_allow_degraded",
    "internal_review": "engine_internal_review",
    "product_candidate": "engine_release_candidate",
    "ship_blocking": "engine_ship_blocking",
}


def _normalize_profile(profile: str) -> str:
    return _LEGACY_PROFILE_ALIAS.get(profile, profile)


def evaluate_bundle(
    bundle_dir: Path,
    *,
    profile: str,
    gold_failed: int | None = None,
    schema_ok: bool | None = None,
    audit_path: Path | None = None,
) -> dict[str, Any]:
    """
    Produce gate decision dict (write as ``11_calibration_release_gate.json``).

    Profiles (engine-neutral):
      - exploratory_allow_degraded
      - engine_internal_review
      - engine_release_candidate
      - engine_ship_blocking

    Legacy aliases are accepted:
      research_allow_degraded | internal_review | product_candidate | ship_blocking
    """
    bundle_dir = bundle_dir.resolve()
    profile = _normalize_profile(profile)
    checks: list[dict[str, Any]] = []

    def _load(name: str) -> dict[str, Any] | None:
        p = bundle_dir / name
        if not p.is_file():
            checks.append({"check": f"file_present:{name}", "pass": False})
            return None
        checks.append({"check": f"file_present:{name}", "pass": True})
        return json.loads(p.read_text(encoding="utf-8"))

    m = _load("00_manifest.json")
    if m is None:
        if profile == "exploratory_allow_degraded":
            return {
                "run": "main_engine_release_gate_v1",
                "profile": profile,
                "pass": True,
                "checks": checks,
                "blocking_reason": None,
                "rollback_advice": "",
                "last_known_good_hint": "exploratory_allow_degraded: manifest optional",
                "operational_envelope": default_operational_envelope(),
            }
        return {
            "run": "main_engine_release_gate_v1",
            "profile": profile,
            "pass": False,
            "checks": checks,
            "blocking_reason": "missing_manifest",
            "rollback_advice": "Run engine workflow to produce 00_manifest.json",
            "last_known_good_hint": "see docs/specs/calibration_release_gate_v1.md",
            "operational_envelope": codes_to_envelope(["G004_MISSING_BUNDLE_MANIFEST"]),
        }
    envs: list[dict[str, Any]] = []
    topology = None
    for fn in ("01_structural_batch.json", "05_sealed_multiscale.json", "06_product_analyze.json"):
        d = _load(fn)
        if isinstance(d, dict) and "operational_envelope" in d:
            envs.append(d["operational_envelope"])
    topology = _load("09_session_topology.json")
    reconciliation = _load("13_contradiction_reconciliation.json")

    blocking_any = any(e.get("blocking") for e in envs if isinstance(e, dict))
    failed_status = any(str(e.get("status")) == "failed" for e in envs if isinstance(e, dict))

    checks.append({"check": "operational_envelope_present_core_artifacts", "pass": len(envs) >= 3})
    checks.append({"check": "no_blocking_anomaly", "pass": not blocking_any})

    consistency = None
    ap = audit_path or (bundle_dir / "10_calibration_audit.json")
    if ap.is_file():
        aud = json.loads(ap.read_text(encoding="utf-8"))
        consistency = float(aud.get("consistency_score") or 0.0)
        checks.append({"check": "calibration_audit_consistency", "pass": True, "value": consistency})

    calibration_block = (
        (m.get("engine_signal_calibration") or m.get("tfp_signal_calibration") or {})
        if isinstance(m, dict)
        else {}
    )
    loaded_cfg = calibration_block.get("loaded_config") or {}
    inhibition_matrix = calibration_block.get("inhibition_matrix") or {}
    operator_path_id = str(
        calibration_block.get("invariant_path_id") or loaded_cfg.get("invariant_path_id") or ""
    )
    _allowed_operator_ids = frozenset(
        {"tfp_invariant_activation_v2", "engine_invariant_activation_v2"},
    )
    checks.append(
        {
            "check": "operator_path_used",
            "pass": operator_path_id in _allowed_operator_ids,
            "value": operator_path_id or None,
        }
    )
    checks.append(
        {
            "check": "calibration_config_present",
            "pass": bool(calibration_block.get("config_version") or loaded_cfg.get("version")),
            "value": calibration_block.get("config_version") or loaded_cfg.get("version"),
        }
    )
    checks.append(
        {
            "check": "coupling_matrix_present",
            "pass": bool(inhibition_matrix.get("version") and inhibition_matrix.get("area_ids")),
            "value": inhibition_matrix.get("version"),
        }
    )
    checks.append(
        {
            "check": "post_operator_feedback_active",
            "pass": bool(loaded_cfg.get("hex_feedback_required")),
            "value": loaded_cfg.get("hex_feedback_required"),
        }
    )
    topology_enabled = bool((m.get("flags") or {}).get("with_topology"))
    topology_sessions = (topology or {}).get("sessions") or []
    topology_meta = (
        (((topology_sessions[0] or {}).get("session_topology") or {}).get("curve_projection_meta") or {})
        if topology_sessions
        else {}
    )
    checks.append(
        {
            "check": "dynamics_metadata_when_topology_enabled",
            "pass": (not topology_enabled) or bool(topology_meta.get("temporal_momentum")),
            "value": topology_meta.get("temporal_momentum"),
        }
    )
    if ap.is_file():
        aud = json.loads(ap.read_text(encoding="utf-8"))
        audit_alarms = set(aud.get("alarms") or [])
        checks.append(
            {
                "check": "audit_operator_path_not_bypassed",
                "pass": "INVARIANT_PATH_NOT_USED" not in audit_alarms,
                "value": sorted(audit_alarms),
            }
        )

    if isinstance(reconciliation, dict):
        rec_sessions = reconciliation.get("sessions") or []
        if not isinstance(rec_sessions, list):
            rec_sessions = []
        canonical_source = reconciliation.get("canonical_source")
        per_session_ratio: dict[str, float] = {}
        per_session_zero_lex: dict[str, float] = {}
        per_session_inferred: dict[str, float] = {}
        source_mismatches: list[str] = []
        for rec in rec_sessions:
            if not isinstance(rec, dict):
                continue
            sid = str(rec.get("session_id") or "")
            lexical_support = rec.get("lexical_support") or {}
            per_session_ratio[sid] = float(lexical_support.get("contradictions_per_accepted_lexical_hit") or 0.0)
            per_session_zero_lex[sid] = float(lexical_support.get("zero_lexical_evidence_share") or 0.0)
            per_session_inferred[sid] = float(lexical_support.get("inferred_share") or 0.0)
            rec_source = rec.get("canonical_source") or canonical_source
            if rec_source != "12_topology_derived_contradictions":
                source_mismatches.append(sid)
        checks.append(
            {
                "check": "canonical_contradiction_source_locked",
                "pass": bool(rec_sessions) and not source_mismatches,
                "value": {"canonical_source": canonical_source, "mismatched_sessions": source_mismatches},
            }
        )
        checks.append(
            {
                "check": "contradiction_overproduction_guard",
                "pass": all(v <= 5.0 for v in per_session_ratio.values()),
                "value": per_session_ratio,
            }
        )
        checks.append(
            {
                "check": "contradiction_grounding_zero_lex_share",
                # Family-granularity share from 13_* lexical_support (coactivation graph grain).
                "pass": all(v <= 0.6 for v in per_session_zero_lex.values()),
                "value": per_session_zero_lex,
            }
        )
        checks.append(
            {
                "check": "contradiction_grounding_inferred_share",
                # Both families ungrounded; same 0.6 bar, now distinct from zero_lex_share.
                "pass": all(v <= 0.6 for v in per_session_inferred.values()),
                "value": per_session_inferred,
            }
        )

    if schema_ok is not None:
        checks.append({"check": "json_schema_validation", "pass": schema_ok})

    if gold_failed is not None:
        checks.append({"check": "goldset_zero_failures", "pass": gold_failed == 0, "value": gold_failed})

    required_engine_checks = {
        "operator_path_used",
        "calibration_config_present",
        "coupling_matrix_present",
        "post_operator_feedback_active",
        "dynamics_metadata_when_topology_enabled",
        "audit_operator_path_not_bypassed",
        "canonical_contradiction_source_locked",
        "contradiction_overproduction_guard",
        "contradiction_grounding_zero_lex_share",
        "contradiction_grounding_inferred_share",
    }
    engine_checks_ok = all(
        c.get("pass") is True for c in checks if c.get("check") in required_engine_checks
    )

    # Profile rules
    pass_gate = all(c.get("pass") is True for c in checks if c.get("pass") is not None)
    if profile == "exploratory_allow_degraded":
        pass_gate = True
    elif profile == "engine_internal_review":
        pass_gate = not blocking_any and not failed_status and engine_checks_ok
    elif profile == "engine_release_candidate":
        pass_gate = (
            not blocking_any
            and not failed_status
            and engine_checks_ok
            and (schema_ok is not False)
            and (consistency is None or consistency >= 0.5)
            and (gold_failed is None or gold_failed == 0)
        )
    elif profile == "engine_ship_blocking":
        pass_gate = (
            not blocking_any
            and not failed_status
            and engine_checks_ok
            and (schema_ok is not False)
            and (gold_failed is None or gold_failed == 0)
            and (consistency is None or consistency >= 0.75)
        )

    blocking_reason = None
    rollback_advice = ""
    if not pass_gate:
        blocking_reason = "one_or_more_gate_checks_failed"
        rollback_advice = (
            "Re-run file pipeline on current main; verify calibration Task2 patches; "
            "see docs/specs/calibration_release_gate_v1.md"
        )

    gate_codes: list[str] = []
    if blocking_any:
        gate_codes.append("G001_BLOCKING_ANOMALY")
    if failed_status:
        gate_codes.append("G002_FAILED_PLANE_STATUS")
    if schema_ok is False:
        gate_codes.append("G003_SCHEMA_INVALID")
    if operator_path_id not in _allowed_operator_ids:
        gate_codes.append("G005_INVARIANT_PATH_BYPASSED")
    if not (inhibition_matrix.get("version") and inhibition_matrix.get("area_ids")):
        gate_codes.append("G006_INHIBITION_MATRIX_MISSING")
    if not (calibration_block.get("config_version") or loaded_cfg.get("version")):
        gate_codes.append("G007_CONFIG_VERSION_MISSING")
    if not bool(loaded_cfg.get("hex_feedback_required")):
        gate_codes.append("G008_POST_HEX_PATH_INACTIVE")
    if topology_enabled and not topology_meta.get("temporal_momentum"):
        gate_codes.append("G009_TEMPORAL_MOMENTUM_METADATA_MISSING")

    out: dict[str, Any] = {
        "run": "main_engine_release_gate_v1",
        "profile": profile,
        "pass": pass_gate,
        "checks": checks,
        "blocking_reason": blocking_reason,
        "rollback_advice": rollback_advice,
        "last_known_good_hint": "release/v0.5.1 sealed product proof (separate from TFP research bundle)",
        "operational_envelope": codes_to_envelope(gate_codes)
        if gate_codes
        else aggregate_file_envelope(envs)
        if envs
        else default_operational_envelope(),
    }
    if consistency is not None:
        out["consistency_score_observed"] = consistency
    return out


def write_gate_report(bundle_dir: Path, body: dict[str, Any]) -> Path:
    p = bundle_dir / "11_calibration_release_gate.json"
    p.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p
