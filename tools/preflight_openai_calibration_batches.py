#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Cross-check batch dirs and expected artifact names (T1 / T2 / summarize)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BUNDLE_KEYS = (
    "02_session_tfp_stages.json",
    "04_dlcr_full.json",
    "05_sealed_multiscale.json",
    "06_product_analyze.json",
    "09_session_topology.json",
)


def _resolve_base(repo: Path, base_arg: Path | None) -> Path:
    if base_arg is not None:
        return base_arg.resolve()
    env_base = os.environ.get("BASE", "").strip()
    if env_base:
        return Path(env_base).resolve()
    return (repo / "outputs/openai_calibration/noone2_cleaned").resolve()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Preflight: verify outputs/openai_calibration/.../batches/batch_* layout and files."
    )
    ap.add_argument("--repo", type=Path, default=None, help="Repo root (default: parent of tools/)")
    ap.add_argument(
        "--base",
        type=Path,
        default=None,
        help="Staging root (default: env BASE or outputs/openai_calibration/noone2_cleaned)",
    )
    ap.add_argument(
        "--require",
        choices=("slice", "bundle", "openai"),
        default="openai",
        help="slice=sessions+corpus; bundle=+DONE_bundle+5 bundle JSONs; openai=+DONE_openai+audit (default)",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any batch fails the --require level",
    )
    args = ap.parse_args()

    repo = (args.repo or Path(__file__).resolve().parents[1]).resolve()
    os.chdir(repo)
    base = _resolve_base(repo, args.base)
    batches_root = base / "batches"

    print(f"base      {base}")
    print(f"batches   {batches_root}")
    if not batches_root.is_dir():
        print("ERROR: batches/ missing", file=sys.stderr)
        return 2

    batches = sorted(p for p in batches_root.iterdir() if p.is_dir() and p.name.startswith("batch_"))
    if not batches:
        print("ERROR: no batch_* dirs", file=sys.stderr)
        return 2

    hdr = (
        f"{'batch':<12} {'sess':>4} {'corp':>4} {'DONEb':>5} "
        f"{'b02':>3} {'b04':>3} {'b05':>3} {'b06':>3} {'b09':>3} "
        f"{'DOai':>4} {'audit':>5}"
    )
    print(hdr)
    print("-" * len(hdr))

    failed = False
    for p in batches:
        sess = (p / "sessions.json").is_file()
        corp = (p / "corpus.jsonl").is_file()
        done_b = (p / "DONE_bundle").is_file()
        bd = p / "bundle"
        b02 = (bd / BUNDLE_KEYS[0]).is_file()
        b04 = (bd / BUNDLE_KEYS[1]).is_file()
        b05 = (bd / BUNDLE_KEYS[2]).is_file()
        b06 = (bd / BUNDLE_KEYS[3]).is_file()
        b09 = (bd / BUNDLE_KEYS[4]).is_file()
        bundle_ok = done_b and b02 and b04 and b05 and b06 and b09
        done_o = (p / "DONE_openai").is_file()
        audit = (p / "openai" / "calibration_audit.json").is_file()

        def yn(x: bool) -> str:
            return "Y" if x else "-"

        print(
            f"{p.name:<12} {yn(sess):>4} {yn(corp):>4} {yn(done_b):>5} "
            f"{yn(b02):>3} {yn(b04):>3} {yn(b05):>3} {yn(b06):>3} {yn(b09):>3} "
            f"{yn(done_o):>4} {yn(audit):>5}"
        )

        if args.require == "slice":
            ok = sess and corp
        elif args.require == "bundle":
            ok = sess and corp and bundle_ok
        else:
            ok = sess and corp and bundle_ok and done_o and audit

        if not ok:
            failed = True

    print("---")
    print("Legend: sess=sessions.json corp=corpus.jsonl DONEb=DONE_bundle b02..b09=bundle/*.json")
    print("        DOai=DONE_openai audit=openai/calibration_audit.json")
    print(f"require={args.require}" + (" strict=ON" if args.strict else ""))

    if failed and args.strict:
        print("PREFLIGHT FAIL: one or more batches miss required artifacts", file=sys.stderr)
        return 1
    if failed:
        print("WARN: one or more batches incomplete for this --require (exit 0; use --strict to fail)")
        return 0
    print("PREFLIGHT OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
