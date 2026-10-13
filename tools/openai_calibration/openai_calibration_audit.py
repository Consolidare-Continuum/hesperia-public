#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from openai_calibration_utils import log_stderr, log_tool_banner, save_json, timestamp_dir


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_str(x: Any) -> str | None:
    return x if isinstance(x, str) and x else None


def _area_idx(area_id: str) -> int | None:
    if not isinstance(area_id, str) or not area_id.startswith("A"):
        return None
    try:
        n = int(area_id[1:])
    except Exception:
        return None
    if 1 <= n <= 12:
        return n - 1
    return None


def _safe_absdiff(a: Any, b: Any) -> float | None:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(abs(float(a) - float(b)))
    return None


def _load_report(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    obj = _read_json(path)
    return obj if isinstance(obj, dict) else None


def _load_tfp_values_list(repo_root: Path) -> dict[str, Any]:
    p = repo_root / "docs" / "specs" / "TFP_VALUES_LIST"
    if not p.is_file():
        return {"found": False}
    txt = p.read_text(encoding="utf-8")
    knob_doc = "docs/specs/TFP_CALIBRATION_KNOBS_v0_1.md" if "TFP_CALIBRATION_KNOBS_v0_1.md" in txt else None
    return {"found": True, "knob_doc": knob_doc}


def main() -> int:
    ap = argparse.ArgumentParser(description="Cross-plane + OpenAI agreement audit (diagnostics-only).")
    ap.add_argument("--bundle-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--openai-dir", type=Path, default=None, help="Dir containing prior OpenAI reports (default: --out)")
    ap.add_argument("--area", type=str, default="A4")
    ap.add_argument("--sealed-threshold", type=float, default=0.2)
    ap.add_argument("--openai-threshold", type=float, default=0.25)
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    tfp_values = _load_tfp_values_list(repo_root)

    bundle_dir = args.bundle_dir.resolve()
    sealed_path = bundle_dir / "05_sealed_multiscale.json"
    prod_path = bundle_dir / "06_product_analyze.json"
    topo_path = bundle_dir / "09_session_topology.json"
    for p in (sealed_path, prod_path, topo_path):
        if not p.is_file():
            raise SystemExit(json.dumps({"error": "missing_bundle_artifact", "path": str(p)}))

    out_dir = args.out.resolve() if args.out else timestamp_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    openai_dir = args.openai_dir.resolve() if args.openai_dir else out_dir

    log_tool_banner(
        "openai_calibration_audit",
        bundle_dir=str(bundle_dir),
        openai_dir=str(openai_dir),
        out_dir=str(out_dir),
    )

    dict_a_rep = _load_report(openai_dir / "dict_a_report.json")
    area_rep = _load_report(openai_dir / "area_calibration_report.json")
    topo_rep = _load_report(openai_dir / "topology_report.json")

    sealed = _read_json(sealed_path)
    prod = _read_json(prod_path)
    topo = _read_json(topo_path)

    sealed_sessions = sealed.get("sessions") if isinstance(sealed, dict) else None
    prod_sessions = prod.get("sessions") if isinstance(prod, dict) else None
    topo_sessions = topo.get("sessions") if isinstance(topo, dict) else None
    if not isinstance(sealed_sessions, list) or not isinstance(prod_sessions, list) or not isinstance(topo_sessions, list):
        raise SystemExit(json.dumps({"error": "invalid_bundle_json", "bundle_dir": str(bundle_dir)}))

    sealed_by_sid: dict[str, dict[str, Any]] = {}
    for s in sealed_sessions:
        if isinstance(s, dict):
            sid = _as_str(s.get("session_id"))
            if sid:
                sealed_by_sid[sid] = s

    prod_by_sid: dict[str, dict[str, Any]] = {}
    for s in prod_sessions:
        if isinstance(s, dict):
            sid = _as_str(s.get("session_id"))
            if sid:
                prod_by_sid[sid] = s

    topo_by_sid: dict[str, dict[str, Any]] = {}
    for s in topo_sessions:
        if isinstance(s, dict):
            sid = _as_str(s.get("session_id"))
            st = s.get("session_topology")
            if sid and isinstance(st, dict):
                topo_by_sid[sid] = st

    # Pull OpenAI per-session area mean (if present).
    openai_area_by_sid: dict[str, float] = {}
    if area_rep and isinstance(area_rep.get("sessions"), list):
        for s in area_rep["sessions"]:
            if not isinstance(s, dict):
                continue
            sid = _as_str(s.get("session_id"))
            if not sid:
                continue
            m = s.get("openai_areas_mean")
            if isinstance(m, dict) and isinstance(m.get(args.area), (int, float)):
                openai_area_by_sid[sid] = float(m[args.area])

    # Pull topology summary per session (if present).
    topo_drift_by_sid: dict[str, float] = {}
    if topo_rep and isinstance(topo_rep.get("sessions"), list):
        for s in topo_rep["sessions"]:
            if not isinstance(s, dict):
                continue
            sid = _as_str(s.get("session_id"))
            if not sid:
                continue
            v = s.get("drift_mae")
            if isinstance(v, (int, float)):
                topo_drift_by_sid[sid] = float(v)

    # Rules.
    failures: list[dict[str, Any]] = []
    suspects: list[dict[str, Any]] = []
    per_session: list[dict[str, Any]] = []

    ai_area_idx = _area_idx(args.area)
    if ai_area_idx is None:
        raise SystemExit(json.dumps({"error": "invalid_area", "area": args.area}))

    def _sealed_area(s: dict[str, Any]) -> float | None:
        vec = s.get("area_activation_vector")
        if isinstance(vec, list) and len(vec) > ai_area_idx and isinstance(vec[ai_area_idx], (int, float)):
            return float(vec[ai_area_idx])
        return None

    def _topology_area_mean(st: dict[str, Any]) -> float | None:
        segs = st.get("segments")
        if not isinstance(segs, list) or not segs:
            return None
        vals: list[float] = []
        for seg in segs:
            if not isinstance(seg, dict):
                continue
            areas = seg.get("areas")
            if isinstance(areas, dict) and isinstance(areas.get(args.area), (int, float)):
                vals.append(float(areas[args.area]))
        if not vals:
            return None
        return sum(vals) / len(vals)

    all_sids = sorted(set(sealed_by_sid) | set(prod_by_sid) | set(topo_by_sid) | set(openai_area_by_sid))
    checks_total = 0
    checks_pass = 0

    for sid in all_sids:
        s_sealed = sealed_by_sid.get(sid)
        s_prod = prod_by_sid.get(sid)
        s_topo = topo_by_sid.get(sid)

        sealed_a = _sealed_area(s_sealed) if s_sealed else None
        topo_a = _topology_area_mean(s_topo) if s_topo else None
        openai_a = openai_area_by_sid.get(sid)
        prod_dom = _as_str(((s_prod or {}).get("result") or {}).get("dominant_area"))

        sess_rec: dict[str, Any] = {
            "session_id": sid,
            "sealed_area": sealed_a,
            "topology_area_mean": topo_a,
            "openai_area_mean": openai_a,
            "product_dominant_area": prod_dom,
            "topology_drift_mae": topo_drift_by_sid.get(sid),
        }

        # Rule 1: sealed vs topology internal agreement (same layer family).
        d1 = _safe_absdiff(sealed_a, topo_a)
        if d1 is not None:
            checks_total += 1
            if d1 < args.sealed_threshold:
                checks_pass += 1
            else:
                failures.append(
                    {
                        "rule": "abs(sealed - topology) < sealed_threshold",
                        "session_id": sid,
                        "lhs": sealed_a,
                        "rhs": topo_a,
                        "abs_diff": d1,
                        "threshold": args.sealed_threshold,
                        "recommended_layer": "topology",
                        "knob_doc": "docs/specs/TFP_CALIBRATION_KNOBS_v0_1.md",
                        "knobs": ["session_topology_run_params", "CURVE_CALIBRATION_REFERENCE"],
                    }
                )

        # Rule 2: sealed vs OpenAI (area calibration agreement).
        d2 = _safe_absdiff(sealed_a, openai_a)
        if d2 is not None:
            checks_total += 1
            if d2 < args.openai_threshold:
                checks_pass += 1
            else:
                failures.append(
                    {
                        "rule": "abs(sealed - openai) < openai_threshold",
                        "session_id": sid,
                        "lhs": sealed_a,
                        "rhs": openai_a,
                        "abs_diff": d2,
                        "threshold": args.openai_threshold,
                        "recommended_layer": "areas",
                        "knob_doc": "docs/specs/TFP_CALIBRATION_KNOBS_v0_1.md",
                        "knobs": ["evidence_volume_normalize", "per_concept_score_cap", "normalize_scores"],
                    }
                )

        # Rule 3: topology report drift suggests topology layer.
        drift = topo_drift_by_sid.get(sid)
        if isinstance(drift, float) and drift > 0.35:
            suspects.append(
                {
                    "session_id": sid,
                    "suspect": "high_openai_topology_drift",
                    "value": drift,
                    "recommended_layer": "topology",
                    "knobs": ["session_topology_run_params", "AREA_CURVE_MAP"],
                }
            )

        sess_rec["rules_checked"] = int((d1 is not None) + (d2 is not None))
        per_session.append(sess_rec)

    # Dict-A quality heuristic (from report-level metrics).
    if dict_a_rep and isinstance(dict_a_rep.get("metrics"), dict):
        m = dict_a_rep["metrics"]
        fp = m.get("false_positives")
        fn = m.get("false_negatives")
        segs = m.get("segments_evaluated") or 1
        if isinstance(fp, int) and isinstance(fn, int) and isinstance(segs, int) and segs > 0:
            err_rate = (fp + fn) / max(1, segs)
            if err_rate > 1.0:
                suspects.append(
                    {
                        "suspect": "high_dict_a_mismatch_rate",
                        "value": err_rate,
                        "recommended_layer": "dict_a",
                        "knobs": ["Dict-A YAML marker weights", "CONFIDENCE_TYPE_MULTIPLIER", "DLCR negation window/multiplier"],
                    }
                )

    agreement_score = (checks_pass / checks_total) if checks_total else 0.0

    # Decide recommended layer (simple: most frequent in failures/suspects).
    layer_votes: dict[str, int] = {"dict_a": 0, "areas": 0, "topology": 0}
    for f in failures:
        layer = f.get("recommended_layer")
        if isinstance(layer, str) and layer in layer_votes:
            layer_votes[layer] += 2
    for s in suspects:
        layer = s.get("recommended_layer")
        if isinstance(layer, str) and layer in layer_votes:
            layer_votes[layer] += 1
    recommended_layer = max(layer_votes.keys(), key=lambda k: (layer_votes[k], k))

    audit = {
        "tool": "openai_calibration_audit.py",
        "bundle_dir": str(bundle_dir),
        "out_dir": str(out_dir),
        "openai_dir": str(openai_dir),
        "tfp_values_list": tfp_values,
        "agreement_score": agreement_score,
        "checks": {"passed": checks_pass, "total": checks_total},
        "failures": failures,
        "suspects": suspects,
        "recommended_layer": recommended_layer,
        "layer_votes": layer_votes,
        "notes": {
            "area_interpretation": {
                "area": args.area,
                "sealed_source": "05_sealed_multiscale.json:sessions[].area_activation_vector[index]",
                "topology_source": "09_session_topology.json:sessions[].session_topology.segments[].areas[area]",
                "openai_source": "area_calibration_report.json:sessions[].openai_areas_mean[area]",
            }
        },
        "inputs_found": {
            "dict_a_report": bool(dict_a_rep),
            "area_report": bool(area_rep),
            "topology_report": bool(topo_rep),
        },
        "sessions": per_session,
        "artifacts": {"report_json": str(out_dir / "calibration_audit.json")},
    }

    save_json(out_dir / "calibration_audit.json", audit)
    ch = audit["checks"]
    log_stderr(
        f"[openai_calibration_audit] done agreement={audit['agreement_score']:.3f} "
        f"checks_pass={ch['passed']}/{ch['total']} failures={len(audit['failures'])} "
        f"recommended_layer={audit['recommended_layer']}"
    )
    print(json.dumps({"out_dir": str(out_dir), "report": str(out_dir / "calibration_audit.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
