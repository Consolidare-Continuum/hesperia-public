#!/usr/bin/env python3
# HESPERIA — RAD. Gena: one-shot TFP file → bundle + audit + schema + optional gold + release gate.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Run ``run_tfp_file_pipeline`` then post-steps so another session attempt is fully wired.

Usage::

  python3 tools/gena_tfp_bundle_run.py -i tests/fixtures/clinical_tfp/tfp_ru_session_sample.md
  python3 tools/gena_tfp_bundle_run.py -i path/to/note.md -o outputs/my_named_run --with-kme --with-gold

Default output directory: ``outputs/tfp/runs/tfp_gena_<input_stem>/`` (override with ``-o``). Same repo also has ``tfp_pipeline_standard_run`` with a **different** default path — see ``docs/specs/TFP_VALUES_LIST`` §0.

Post-steps (unless ``--pipeline-only``): ``tfp_calibration_audit`` → ``validate_tfp_bundle_schemas`` →
optional goldset (``--with-gold``) → ``calibration_release_gate`` (writes ``11_…``).

Exit codes: ``2`` pipeline failed; ``3`` schema validation failed; ``4`` goldset failed (with ``--with-gold``);
``0`` success.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _py(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(REPO),
        env=env,
        capture_output=capture,
        text=True,
        check=False,
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Gena TFP: file/json in → full artifact bundle + calibration discipline (audit, schema, gate)."
    )
    ap.add_argument("--input", "-i", type=Path, required=True)
    ap.add_argument(
        "--out-dir",
        "-o",
        type=Path,
        default=None,
        help="Bundle directory (default: outputs/tfp/runs/tfp_gena_<input_stem>)",
    )
    ap.add_argument("--pipeline-only", action="store_true", help="Only run run_tfp_file_pipeline")
    ap.add_argument("--with-gold", action="store_true", help="Run tests/gold/tfp_calibration_goldset_v1.json (pinned session)")
    ap.add_argument(
        "--gate-profile",
        default="internal_review",
        choices=[
            "research_allow_degraded",
            "internal_review",
            "product_candidate",
            "ship_blocking",
        ],
    )
    ap.add_argument("--relax-discipline", action="store_true", help="Do not exit non-zero on schema/gold failures")
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
    ap.add_argument(
        "--skip-triz-activation",
        action="store_true",
        help="Forward to file pipeline: skip 12_* triz_activation files when --with-topology",
    )
    ap.add_argument(
        "--contradiction-calibration-json",
        type=Path,
        default=None,
        help="Optional path to contradiction calibration profile (forwarded to run_tfp_file_pipeline)",
    )
    args = ap.parse_args()

    inp = args.input.resolve()
    if not inp.is_file():
        print(f"ERROR: input not a file: {inp}", file=sys.stderr)
        return 2

    stem = inp.stem or "session"
    out_dir = args.out_dir
    if out_dir is None:
        out_dir = REPO / "outputs" / "tfp" / "runs" / f"tfp_gena_{stem}"
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pipe_cmd = [
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
    if args.contradiction_calibration_json is not None:
        pipe_cmd.extend(["--contradiction-calibration-json", str(args.contradiction_calibration_json.resolve())])

    # Stable run id for manifest when not supplied
    if not os.environ.get("HESPERIA_TFP_PIPELINE_RUN_ID"):
        os.environ["HESPERIA_TFP_PIPELINE_RUN_ID"] = str(uuid.uuid4())

    r0 = _py(pipe_cmd)
    if r0.returncode != 0:
        if r0.stderr:
            print(r0.stderr, file=sys.stderr, end="")
        if r0.stdout:
            print(r0.stdout, file=sys.stderr, end="")
        return 2

    print(f"gena_tfp_bundle_run: pipeline OK → {out_dir}", file=sys.stderr)

    if args.pipeline_only:
        print(str(out_dir))
        return 0

    r_audit = _py([str(REPO / "tools" / "tfp_calibration_audit.py"), "--bundle-dir", str(out_dir)])
    if r_audit.stderr:
        print(r_audit.stderr, file=sys.stderr, end="")

    r_schema = _py([str(REPO / "tools" / "validate_tfp_bundle_schemas.py"), "--bundle-dir", str(out_dir)])
    schema_ok = r_schema.returncode == 0
    if r_schema.stderr:
        print(r_schema.stderr, file=sys.stderr, end="")

    gold_failed: int | None = None
    if args.with_gold:
        r_g = _py(
            [str(REPO / "tools" / "run_tfp_calibration_goldset.py"), "--bundle-dir", str(out_dir)],
            capture=True,
        )
        try:
            rep = json.loads(r_g.stdout)
            gold_failed = int(rep.get("failed") or 0)
        except (json.JSONDecodeError, TypeError, ValueError):
            gold_failed = 999
        if r_g.stderr:
            print(r_g.stderr, file=sys.stderr, end="")
        print(r_g.stdout, end="")

    from hesperia.engine.calibration_release_gate import evaluate_bundle, write_gate_report

    body = evaluate_bundle(
        out_dir,
        profile=args.gate_profile,
        gold_failed=gold_failed,
        schema_ok=schema_ok,
    )
    gate_path = write_gate_report(out_dir, body)
    print(json.dumps(body, indent=2, ensure_ascii=False))
    print(f"gena_tfp_bundle_run: gate → {gate_path}", file=sys.stderr)

    if args.relax_discipline:
        print(str(out_dir))
        return 0

    if not schema_ok:
        return 3
    if args.with_gold and gold_failed not in (0, None):
        return 4
    if not body.get("pass"):
        return 5

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
