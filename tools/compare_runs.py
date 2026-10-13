#!/usr/bin/env python3
"""Compare two run dossiers and report module influence deltas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _delta_map(a: dict, b: dict) -> dict[str, float]:
    keys = sorted(set(a.keys()) | set(b.keys()))
    return {k: float(b.get(k, 0.0)) - float(a.get(k, 0.0)) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare two dossier runs.")
    ap.add_argument("run_a")
    ap.add_argument("run_b")
    args = ap.parse_args()
    a = _load(Path(args.run_a))
    b = _load(Path(args.run_b))
    area_shift = _delta_map(dict(a.get("areas") or {}), dict(b.get("areas") or {}))
    tension_delta = float((b.get("metrics") or {}).get("tension", 0.0)) - float((a.get("metrics") or {}).get("tension", 0.0))
    dominant_change = {
        "area": ((a.get("metrics") or {}).get("dominant_area"), (b.get("metrics") or {}).get("dominant_area")),
        "family": ((a.get("metrics") or {}).get("dominant_family"), (b.get("metrics") or {}).get("dominant_family")),
    }
    out = {"area_shift": area_shift, "tension_delta": tension_delta, "dominant_change": dominant_change}
    print(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

