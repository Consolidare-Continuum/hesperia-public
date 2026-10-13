#!/usr/bin/env python3
# HESPERIA — Standard TFP file pipeline + optional bundle inspect + conflict release gating (v0.5.8 task9).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Thin wrapper around ``runtime.pipeline.run_tfp_file_pipeline`` with optional inspection
and promotion gating exit codes.

Writes ``99_tfp_bundle_inspect.json`` when ``--inspect`` is set, and optionally merges
``conflict_release_summary`` into ``20_main_engine_full_context.json`` and ``00_manifest.json``.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def check_conflict_gate_exit(
    report: dict[str, Any],
    *,
    fail_on_conflict_gate: bool,
    min_conflict_integrity_score: float | None,
) -> int:
    """Return non-zero exit code when optional gates fail (0 = ok). Pure helper for tests."""
    if fail_on_conflict_gate and report.get("promotion_conflict_verdict") == "FAIL":
        return 5
    if min_conflict_integrity_score is not None:
        thr = float(min_conflict_integrity_score)
        score = float(report.get("conflict_integrity_score") or 0.0)
        if score < thr:
            return 6
    return 0


def _merge_conflict_summary(out_dir: Path, summary: dict[str, Any], report: dict[str, Any] | None = None) -> None:
    contract_summary = None
    if isinstance(report, dict):
        contract_summary = {
            "spec_version": report.get("contradiction_contract_spec_version"),
            "contract_valid": report.get("contradiction_contract_valid"),
            "authoritative_artifact": "20_main_engine_full_context.json",
            "inspection_artifact": "99_tfp_bundle_inspect.json",
            "missing_required_fields": report.get("missing_required_contradiction_fields") or [],
            "deprecated_fields_found": report.get("deprecated_contradiction_fields_found") or [],
            "authority_conflicts": report.get("authority_conflicts") or [],
        }

    p20 = out_dir / "20_main_engine_full_context.json"
    if p20.is_file():
        try:
            body = json.loads(p20.read_text(encoding="utf-8"))
            if isinstance(body, dict):
                body["conflict_release_summary"] = summary
                if contract_summary is not None:
                    body["contradiction_contract"] = contract_summary
                _write_json(p20, body)
        except (OSError, json.JSONDecodeError):
            pass
    pm = out_dir / "00_manifest.json"
    if pm.is_file():
        try:
            man = json.loads(pm.read_text(encoding="utf-8"))
            if isinstance(man, dict):
                man["conflict_release_summary"] = summary
                if contract_summary is not None:
                    man["contradiction_contract"] = contract_summary
                _write_json(pm, man)
        except (OSError, json.JSONDecodeError):
            pass


def _py_mod(args: list[str]) -> int:
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    r = subprocess.run(
        [sys.executable, *args],
        cwd=str(REPO),
        env=env,
        check=False,
    )
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser(
        description="TFP standard run: file pipeline + optional inspect + optional conflict-gate exit codes."
    )
    ap.add_argument("--input", "-i", type=Path, default=None, help="Input file (not used with --inspect-bundle-dir)")
    ap.add_argument("--out-dir", "-o", type=Path, default=None)
    ap.add_argument("--inspect", action="store_true", help="Write 99_tfp_bundle_inspect.json and merge summary into bundle")
    ap.add_argument(
        "--inspect-bundle-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Skip pipeline; only run inspect/merge on an existing bundle directory (for CI/tests)",
    )
    ap.add_argument(
        "--fail-on-conflict-gate",
        action="store_true",
        help="Exit non-zero when promotion_conflict_verdict is FAIL (requires --inspect)",
    )
    ap.add_argument(
        "--min-conflict-integrity-score",
        type=float,
        default=None,
        metavar="SCORE",
        help="Exit non-zero when conflict_integrity_score is below SCORE (requires --inspect)",
    )
    ap.add_argument("--with-kme", action="store_true")
    ap.add_argument("--with-triz", action="store_true")
    ap.add_argument("--with-topology", action="store_true")
    ap.add_argument("--with-r1-r4", action="store_true")
    ap.add_argument("--skip-structural", action="store_true")
    ap.add_argument("--skip-stages", action="store_true")
    ap.add_argument("--skip-hex", action="store_true")
    ap.add_argument("--skip-dlcr", action="store_true")
    ap.add_argument("--skip-sealed", action="store_true")
    ap.add_argument("--skip-analyze", action="store_true")
    ap.add_argument("--dlcr-mode", default="clinical_speech")
    ap.add_argument("--no-dlcr-domain-pack", action="store_true")
    ap.add_argument("--skip-triz-activation", action="store_true")
    ap.add_argument("--topology-params-json", type=Path, default=None)
    args = ap.parse_args()

    if args.inspect_bundle_dir is None and args.input is None:
        print("ERROR: provide --input or --inspect-bundle-dir", file=sys.stderr)
        return 2

    if args.inspect_bundle_dir is not None:
        out_dir = args.inspect_bundle_dir.resolve()
        if not out_dir.is_dir():
            print(f"ERROR: --inspect-bundle-dir not a directory: {out_dir}", file=sys.stderr)
            return 2
        from tools.inspect_tfp_bundle_output import inspect_bundle

        report = inspect_bundle(out_dir)
        p99 = out_dir / "99_tfp_bundle_inspect.json"
        _write_json(p99, report)
        summ = report.get("conflict_release_summary") or {}
        _merge_conflict_summary(out_dir, summ, report)
        return check_conflict_gate_exit(
            report,
            fail_on_conflict_gate=args.fail_on_conflict_gate,
            min_conflict_integrity_score=args.min_conflict_integrity_score,
        )

    inp = args.input.resolve()
    if not inp.is_file():
        print(f"ERROR: input not a file: {inp}", file=sys.stderr)
        return 2

    run_id = str(uuid.uuid4())
    os.environ["HESPERIA_TFP_PIPELINE_RUN_ID"] = run_id
    out_dir = args.out_dir
    if out_dir is None:
        out_dir = REPO / "outputs" / "tfp" / "runs" / "tfp_pipeline_run" / run_id
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pipe_cmd: list[str | Path] = [
        "-m",
        "runtime.pipeline.run_tfp_file_pipeline",
        "--input",
        str(inp),
        "--out-dir",
        str(out_dir),
        "--dlcr-mode",
        args.dlcr_mode,
    ]
    if args.with_kme:
        pipe_cmd.append("--with-kme")
    if args.with_triz:
        pipe_cmd.append("--with-triz")
    if args.with_topology:
        pipe_cmd.append("--with-topology")
    if args.with_r1_r4:
        pipe_cmd.append("--with-r1-r4")
    if args.skip_structural:
        pipe_cmd.append("--skip-structural")
    if args.skip_stages:
        pipe_cmd.append("--skip-stages")
    if args.skip_hex:
        pipe_cmd.append("--skip-hex")
    if args.skip_dlcr:
        pipe_cmd.append("--skip-dlcr")
    if args.skip_sealed:
        pipe_cmd.append("--skip-sealed")
    if args.skip_analyze:
        pipe_cmd.append("--skip-analyze")
    if args.no_dlcr_domain_pack:
        pipe_cmd.append("--no-dlcr-domain-pack")
    if args.skip_triz_activation:
        pipe_cmd.append("--skip-triz-activation")
    if args.topology_params_json is not None:
        pipe_cmd.extend(["--topology-params-json", str(args.topology_params_json.resolve())])

    rc = _py_mod(pipe_cmd)
    if rc != 0:
        return rc

    if not args.inspect:
        return 0

    from tools.inspect_tfp_bundle_output import inspect_bundle

    report = inspect_bundle(out_dir)
    p99 = out_dir / "99_tfp_bundle_inspect.json"
    _write_json(p99, report)
    summ = report.get("conflict_release_summary") or {}
    _merge_conflict_summary(out_dir, summ, report)

    ec = check_conflict_gate_exit(
        report,
        fail_on_conflict_gate=args.fail_on_conflict_gate,
        min_conflict_integrity_score=args.min_conflict_integrity_score,
    )
    if ec == 5:
        print("tfp_pipeline_standard_run: conflict gate FAIL (--fail-on-conflict-gate)", file=sys.stderr)
    elif ec == 6:
        thr = float(args.min_conflict_integrity_score or 0.0)
        score = float(report.get("conflict_integrity_score") or 0.0)
        print(
            f"tfp_pipeline_standard_run: conflict_integrity_score {score} < {thr}",
            file=sys.stderr,
        )
    return ec


if __name__ == "__main__":
    raise SystemExit(main())
