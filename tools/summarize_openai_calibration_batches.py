#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Print per-batch OpenAI calibration audit summary (after T2)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Summarize calibration_audit.json + DONE_openai per batch under batches/."
    )
    ap.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Repo root (default: parent of tools/)",
    )
    ap.add_argument(
        "--base",
        type=Path,
        default=None,
        help="Staging root like outputs/.../noone2_cleaned (default: env BASE or openai_calibration/noone2_cleaned under repo)",
    )
    args = ap.parse_args()

    repo = (args.repo or Path(__file__).resolve().parents[1]).resolve()
    os.chdir(repo)

    base = args.base
    if base is None:
        env_base = os.environ.get("BASE", "").strip()
        base = Path(env_base) if env_base else (repo / "outputs/openai_calibration/noone2_cleaned")
    else:
        base = base.resolve()
    batches_root = base / "batches"

    if not batches_root.is_dir():
        print(f"ERROR: batches root missing: {batches_root}", file=sys.stderr)
        return 2

    any_batch = False
    for p in sorted(batches_root.glob("batch_*")):
        if not p.is_dir():
            continue
        any_batch = True
        audit = p / "openai" / "calibration_audit.json"
        done = (p / "DONE_openai").is_file()
        tag = "OK" if done else "no DONE_openai"
        if not audit.is_file():
            print(f"{p.name:12} {tag:16} (no calibration_audit.json)")
            continue
        j = json.loads(audit.read_text(encoding="utf-8"))
        agr = j.get("agreement_score")
        layer = j.get("recommended_layer")
        ch = j.get("checks") or {}
        agr_s = f"{float(agr):.3f}" if isinstance(agr, (int, float)) else str(agr)
        print(
            f"{p.name:12} {tag:16} agreement={agr_s}  recommended_layer={layer}  "
            f"checks={ch.get('passed')}/{ch.get('total')}"
        )

    if not any_batch:
        print(f"(no batch_* under {batches_root})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
