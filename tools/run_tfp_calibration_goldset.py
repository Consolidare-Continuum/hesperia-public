#!/usr/bin/env python3
# HESPERIA — RAD. Goldset runner for TFP calibration (Task 6).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]


def _load(p: Path) -> dict[str, Any] | None:
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _row01(data: dict[str, Any]) -> dict[str, Any] | None:
    rows = data.get("structural_batch") or []
    if not rows:
        return None
    return rows[0]


def _core_structural(row: dict[str, Any]) -> dict[str, Any]:
    pl = row.get("payload")
    return pl if isinstance(pl, dict) else row


def _session_by_stem(bundle_dir: Path, stem: str) -> tuple[dict | None, dict | None, dict | None]:
    s01 = _load(bundle_dir / "01_structural_batch.json") or {}
    s05 = _load(bundle_dir / "05_sealed_multiscale.json") or {}
    s06 = _load(bundle_dir / "06_product_analyze.json") or {}
    struct_row = None
    for r in s01.get("structural_batch") or []:
        if str(r.get("session_id")) == stem:
            struct_row = r
            break
    sealed = None
    for r in s05.get("sessions") or []:
        if str(r.get("session_id")) == stem:
            sealed = r
            break
    an = None
    for r in s06.get("sessions") or []:
        if str(r.get("session_id")) == stem:
            an = r
            break
    return struct_row, sealed, an


def run_goldset(bundle_dir: Path, gold_path: Path, *, verbose: bool) -> dict[str, Any]:
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    passed = 0
    failed = 0

    for case in gold.get("aggregation_gold") or []:
        stem = str(case.get("session_stem") or "")
        st, se, an = _session_by_stem(bundle_dir, stem)
        deltas: list[str] = []
        ok = True

        if case.get("expected_sealed_hex_total_mass_min") is not None and se:
            need = float(case["expected_sealed_hex_total_mass_min"])
            mass = float((se.get("hex_activation_map") or {}).get("total_mass") or 0.0)
            if mass < need:
                ok = False
                deltas.append(f"sealed_hex_mass {mass} < {need}")

        if case.get("expected_structural_l1_coverage_min") is not None and st:
            need = float(case["expected_structural_l1_coverage_min"])
            L1 = (_core_structural(st).get("L1") or {})
            cov = float(L1.get("COVERAGE_RATIO") or 0.0)
            if cov < need:
                ok = False
                deltas.append(f"structural_coverage {cov} < {need}")

        if case.get("expected_analyze_coverage_min") is not None and an:
            need = float(case["expected_analyze_coverage_min"])
            cov = float((an.get("extended") or {}).get("attribution_coverage") or 0.0)
            if cov < need:
                ok = False
                deltas.append(f"analyze_coverage {cov} < {need}")

        top3 = case.get("expected_dominant_stage_areas_top3") or []
        if top3 and st:
            s02 = _load(bundle_dir / "02_session_tfp_stages.json") or {}
            areas = {}
            for row in s02.get("session_tfp_stages") or []:
                if str(row.get("session_id")) == stem:
                    areas = row.get("areas_top") or {}
                    break
            rank = sorted(areas.keys(), key=lambda k: float(areas.get(k) or 0), reverse=True)
            prefix = rank[: len(top3)]
            if prefix != list(top3):
                ok = False
                deltas.append(f"stage_area_rank_drift want_prefix={list(top3)} got_prefix={prefix}")

        if ok:
            passed += 1
        else:
            failed += 1
        entry = {"id": case.get("id"), "pass": ok, "deltas": deltas, "gold_reasoning_note": case.get("gold_reasoning_note")}
        results.append(entry)
        if verbose or not ok:
            print(f"[{'PASS' if ok else 'FAIL'}] {case.get('id')}: {'; '.join(deltas) or 'ok'}", file=sys.stderr)

    # Raw integrity: evaluate forbidden composite using live bundle
    for case in gold.get("raw_integrity_gold") or []:
        stem = str(case.get("session_stem") or "")
        st, se, an = _session_by_stem(bundle_dir, stem)
        bad = False
        reasons: list[str] = []
        if st and an and not an.get("_error"):
            core = _core_structural(st)
            L1 = core.get("L1") or {}
            att = int(L1.get("ATTRIBUTED_TOKENS") or 0)
            fb = bool(
                L1.get("CALIBRATION_FALLBACK_USED")
                or (core.get("diagnostics") or {}).get("calibration_status", {}).get("l1_calibration_fallback")
            )
            cov = float((an.get("extended") or {}).get("attribution_coverage") or 0.0)
            if cov >= 0.95 and att == 0 and not fb:
                bad = True
                reasons.append("split_brain:L1_zero_high_analyze_coverage_no_fallback")
            mass = float((se.get("hex_activation_map") or {}).get("total_mass") or 0.0) if se else 0.0
            if cov >= 0.9 and mass <= 0.0:
                bad = True
                reasons.append("split_brain:zero_hex_mass_high_analyze_coverage")
        if not bad:
            passed += 1
        else:
            failed += 1
        results.append({"id": case.get("id"), "layer": "raw_integrity_gold", "pass": not bad, "deltas": reasons})
        if verbose or bad:
            print(f"[{'PASS' if not bad else 'FAIL'}] {case.get('id')} raw_integrity: {reasons}", file=sys.stderr)

    # Readability: required files have operational_envelope
    for case in gold.get("readability_gold") or []:
        req = case.get("require_operational_envelope_on_artifacts") or []
        bad = False
        reasons = []
        for fn in req:
            data = _load(bundle_dir / fn)
            if not data or "operational_envelope" not in data:
                bad = True
                reasons.append(f"missing_operational_envelope:{fn}")
        if not bad:
            passed += 1
        else:
            failed += 1
        results.append({"id": case.get("id"), "layer": "readability_gold", "pass": not bad, "deltas": reasons})

    return {
        "run": "tfp_calibration_goldset_v1",
        "bundle_dir": str(bundle_dir.resolve()),
        "gold_path": str(gold_path.resolve()),
        "passed": passed,
        "failed": failed,
        "results": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run TFP calibration goldset against a bundle directory.")
    ap.add_argument("--bundle-dir", type=Path, required=True)
    ap.add_argument(
        "--gold",
        type=Path,
        default=REPO / "tests" / "gold" / "tfp_calibration_goldset_v1.json",
    )
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()
    rep = run_goldset(args.bundle_dir.resolve(), args.gold.resolve(), verbose=args.verbose)
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0 if rep["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
