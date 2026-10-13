#!/usr/bin/env python3
# HESPERIA — RAD. CLI for calibration release gate (Task 10).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit 11_calibration_release_gate.json for an engine bundle.")
    ap.add_argument("--bundle-dir", type=Path, required=True)
    ap.add_argument(
        "--profile",
        default="engine_internal_review",
        choices=[
            "exploratory_allow_degraded",
            "engine_internal_review",
            "engine_release_candidate",
            "engine_ship_blocking",
            # Backward-compatible aliases
            "research_allow_degraded",
            "internal_review",
            "product_candidate",
            "ship_blocking",
        ],
    )
    ap.add_argument("--skip-schema", action="store_true")
    ap.add_argument("--skip-gold", action="store_true")
    args = ap.parse_args()
    bd = args.bundle_dir.resolve()

    schema_ok: bool | None = None
    if not args.skip_schema:
        r = subprocess.run(
            [sys.executable, str(REPO / "tools" / "validate_tfp_bundle_schemas.py"), "--bundle-dir", str(bd)],
            cwd=str(REPO),
            capture_output=True,
            text=True,
        )
        schema_ok = r.returncode == 0

    gold_failed: int | None = None
    if not args.skip_gold:
        r2 = subprocess.run(
            [sys.executable, str(REPO / "tools" / "run_tfp_calibration_goldset.py"), "--bundle-dir", str(bd)],
            cwd=str(REPO),
            capture_output=True,
            text=True,
        )
        try:
            rep = json.loads(r2.stdout)
            gold_failed = int(rep.get("failed") or 0)
        except json.JSONDecodeError:
            gold_failed = 999

    from hesperia.engine.calibration_release_gate import evaluate_bundle, write_gate_report

    body = evaluate_bundle(
        bd,
        profile=args.profile,
        gold_failed=gold_failed,
        schema_ok=schema_ok,
    )
    out = write_gate_report(bd, body)
    print(json.dumps(body, indent=2, ensure_ascii=False))
    print(f"wrote {out}", file=sys.stderr)
    return 0 if body.get("pass") else 2


if __name__ == "__main__":
    raise SystemExit(main())
