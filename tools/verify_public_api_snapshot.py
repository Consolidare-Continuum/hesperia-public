#!/usr/bin/env python3
# HESPERIA — Ensure frozen public JSON Schema matches canonical (drift gate).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage (repo root):  python3 tools/verify_public_api_snapshot.py [--repo PATH]

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

_CANONICAL = Path("assets/schemas/public/public_output_schema.json")
_SNAPSHOT = Path("assets/schemas/public_api_v0_5_1.snapshot.json")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify public API schema snapshot matches canonical file.")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    repo = args.repo
    c = repo / _CANONICAL
    s = repo / _SNAPSHOT
    if not c.is_file():
        print(f"missing canonical schema: {c}", file=sys.stderr)
        return 1
    if not s.is_file():
        print(f"missing snapshot: {s}", file=sys.stderr)
        return 1
    cb = c.read_bytes()
    sb = s.read_bytes()
    if cb != sb:
        print(
            "public_api_snapshot_mismatch: "
            f"canonical sha256={_sha256(cb)} bytes={len(cb)} | "
            f"snapshot sha256={_sha256(sb)} bytes={len(sb)}",
            file=sys.stderr,
        )
        print("Regenerate snapshot after intentional schema change:", file=sys.stderr)
        print(f"  cp {_CANONICAL} {_SNAPSHOT}", file=sys.stderr)
        return 1
    print(f"verify_public_api_snapshot: OK ({len(cb)} bytes, sha256={_sha256(cb)[:16]}…)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
