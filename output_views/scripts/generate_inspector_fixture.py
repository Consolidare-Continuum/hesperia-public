#!/usr/bin/env python3
"""Generate `output_views/tests/fixtures/<session_id>.json` from a TFP pipeline bundle dir (OUT-VIEW-FULL-02).

Usage:
  # From pinned CI synthetic bundle (fast, deterministic; goldset stem 1-11-09-2023):
  python3 scripts/generate_inspector_fixture.py --from-ci-bundle

  # From any ``run_tfp_file_pipeline`` output directory:
  python3 scripts/generate_inspector_fixture.py --bundle-dir /path/to/pipeline_out --session-id 1-11-09-2023

  # Run pipeline then build (slow; requires full Hesperia runtime):
  python3 scripts/generate_inspector_fixture.py --run-pipeline --input ../hesperia/modules/tfp/data/tfp_v1/corpus/sessions/11-09-2023.md --out-bundle /tmp/tfp_out

Copyright © 2026 igareosh.com. See Hesperia LEGAL_NOTICE.md.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Session Inspector JSON fixture from TFP pipeline artifacts.")
    ap.add_argument(
        "--from-ci-bundle",
        action="store_true",
        help="Use tests/fixtures/tfp_calibration_bundle_ci (synthetic CI bundle).",
    )
    ap.add_argument("--bundle-dir", type=Path, help="Directory with 00_manifest.json … 06_*.json")
    ap.add_argument("--session-id", type=str, default=None, help="default: first session in manifest")
    ap.add_argument(
        "--fixture-out",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "1-11-09-2023.json",
        help="Output JSON path (default: output_views/tests/fixtures/1-11-09-2023.json)",
    )
    ap.add_argument("--run-pipeline", action="store_true", help="Run run_tfp_file_pipeline before --bundle-dir")
    ap.add_argument("--input", type=Path, help="Transcript for --run-pipeline (e.g. .md)")
    ap.add_argument("--out-bundle", type=Path, help="Pipeline output dir for --run-pipeline")
    args = ap.parse_args()

    bundle_dir: Path | None = None
    if args.from_ci_bundle:
        bundle_dir = REPO_ROOT / "tests" / "fixtures" / "tfp_calibration_bundle_ci"
        sid = args.session_id or "1-11-09-2023"
    elif args.run_pipeline:
        if not args.input or not args.out_bundle:
            raise SystemExit("--run-pipeline requires --input and --out-bundle")
        args.out_bundle.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable,
            "-m",
            "runtime.pipeline.run_tfp_file_pipeline",
            "--input",
            str(args.input.resolve()),
            "--out-dir",
            str(args.out_bundle.resolve()),
        ]
        subprocess.run(cmd, cwd=str(REPO_ROOT), check=True)
        bundle_dir = args.out_bundle
        sid = args.session_id
    elif args.bundle_dir:
        bundle_dir = args.bundle_dir.resolve()
        sid = args.session_id
    else:
        raise SystemExit("Specify --from-ci-bundle, or --bundle-dir, or --run-pipeline with --input/--out-bundle")

    from segment.tfp_pipeline_bundle import write_session_inspector_fixture

    out = write_session_inspector_fixture(bundle_dir, args.fixture_out, session_id=sid)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
