#!/usr/bin/env python3
# HESPERIA — RAD. Deterministic presentation pass from fixed intermediates (Task 5 stub).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Future: load frozen raw bundle + profile id → write presentation-only JSON (no attribution mutation).

v1 stub: validates profile name and prints paths. Golden replay hooks land with frozen intermediates.

Usage::
  python3 tools/apply_output_calibration_profile.py --profile balanced_readable --raw-bundle path/to/raw.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_PROFILES = REPO / "assets" / "config" / "calibration_profiles_v1.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Calibration profile presentation stub (v1).")
    ap.add_argument("--profile", required=True, help="Profile id, e.g. balanced_readable")
    ap.add_argument("--raw-bundle", type=Path, default=None, help="Future: intermediate JSON path")
    args = ap.parse_args()
    data = json.loads(_PROFILES.read_text(encoding="utf-8"))
    profs = data.get("profiles") or {}
    if args.profile not in profs:
        print(f"unknown profile {args.profile!r}; known: {sorted(profs)}", file=sys.stderr)
        return 2
    blob = json.dumps(profs[args.profile], sort_keys=True, ensure_ascii=False).encode()
    h = hashlib.sha256(blob).hexdigest()[:16]
    print(
        json.dumps(
            {
                "profile": args.profile,
                "profile_hash": h,
                "calibration_version": data.get("version"),
                "status": "stub_no_replay_yet",
                "raw_bundle": str(args.raw_bundle) if args.raw_bundle else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
