#!/usr/bin/env python3
# HESPERIA — Fail CI if unreferenced-module count exceeds budget.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: python3 tools/check_dead_weight_budget.py [--repo PATH]

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

_BASELINE_FILE = Path("docs/DEAD_WEIGHT_BASELINE.txt")


def _parse_int_key(text: str, key: str) -> int | None:
    pat = re.compile(rf"^{re.escape(key)}\s*=\s*(\d+)\s*$")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        m = pat.match(line)
        if m:
            return int(m.group(1))
    return None


def _parse_max(text: str) -> int | None:
    return _parse_int_key(text, "MAX_UNREFERENCED")


def _parse_recorded(text: str) -> int | None:
    return _parse_int_key(text, "RECORDED_COUNT")


def _parse_max_increase(text: str) -> int | None:
    return _parse_int_key(text, "MAX_INCREASE_FROM_RECORDED")


def main() -> int:
    ap = argparse.ArgumentParser(description="Enforce dead-weight count budget vs docs/DEAD_WEIGHT_BASELINE.txt")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    repo = args.repo.resolve()
    baseline_path = repo / _BASELINE_FILE
    if not baseline_path.is_file():
        print(f"missing {_BASELINE_FILE}", file=sys.stderr)
        return 1
    raw = baseline_path.read_text(encoding="utf-8")
    mx = _parse_max(raw)
    if mx is None:
        print(f"no MAX_UNREFERENCED= in {_BASELINE_FILE}", file=sys.stderr)
        return 1
    rec = _parse_recorded(raw)
    if rec is None:
        print(f"no RECORDED_COUNT= in {_BASELINE_FILE}", file=sys.stderr)
        return 1
    inc_cap = _parse_max_increase(raw)
    if inc_cap is None:
        print(f"no MAX_INCREASE_FROM_RECORDED= in {_BASELINE_FILE}", file=sys.stderr)
        return 1

    fu = repo / "tools" / "find_unreferenced_files.py"
    spec = importlib.util.spec_from_file_location("find_unreferenced_files", fu)
    if spec is None or spec.loader is None:
        print("cannot load find_unreferenced_files.py", file=sys.stderr)
        return 1
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rels = mod.compute_unreferenced_relpaths(repo)
    n = len(rels)
    if n > mx:
        print(
            f"check_dead_weight_budget: FAIL unreferenced_count={n} > MAX_UNREFERENCED={mx} "
            f"(see {_BASELINE_FILE})",
            file=sys.stderr,
        )
        return 1
    drift = n - rec
    if drift > inc_cap:
        print(
            f"check_dead_weight_budget: FAIL drift={drift} "
            f"(count={n} - RECORDED_COUNT={rec}) > MAX_INCREASE_FROM_RECORDED={inc_cap}. "
            f"Raise RECORDED_COUNT after review or remove dead modules (see {_BASELINE_FILE})",
            file=sys.stderr,
        )
        return 1
    print(
        f"check_dead_weight_budget: OK count={n} max={mx} recorded={rec} drift={drift} drift_cap={inc_cap}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
