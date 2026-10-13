#!/usr/bin/env python3
"""Verify or regenerate golden iteration_segment_openai_v1 snapshot (T53)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# output_views/ as cwd
ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "iteration_segment_openai_v1_iter0.json"
FIXTURE = ROOT / "tests" / "fixtures" / "session_inspector_min.json"


def _build() -> dict:
    sys.path.insert(0, str(ROOT))
    from segment import extract_iteration_segment, finalize_segment_openai_v1

    bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return finalize_segment_openai_v1(extract_iteration_segment(bundle, "iter_0"))


def verify() -> int:
    if not GOLDEN.is_file():
        print("missing golden file:", GOLDEN, file=sys.stderr)
        return 2
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    got = _build()
    if got != expected:
        print("golden mismatch — run: python3 scripts/validate_golden_segment.py regenerate", file=sys.stderr)
        return 1
    print("golden OK")
    return 0


def regenerate() -> int:
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    data = _build()
    GOLDEN.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", GOLDEN)
    return 0


def main() -> int:
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "verify"
    if cmd == "verify":
        return verify()
    if cmd == "regenerate":
        return regenerate()
    print("usage: validate_golden_segment.py verify|regenerate", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
