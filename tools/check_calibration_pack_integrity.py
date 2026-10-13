#!/usr/bin/env python3
"""Check calibration pack integrity for active and historical dict packs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno}: invalid JSONL: {exc}") from exc
    return rows


def _check_pack(pack_dir: Path) -> list[str]:
    errs: list[str] = []
    required = ["dict_a.jsonl", "dict_b.jsonl", "links.jsonl"]
    for name in required:
        p = pack_dir / name
        if not p.is_file():
            errs.append(f"missing {name}")
            continue
        rows = _iter_jsonl(p)
        if not rows:
            errs.append(f"{name} has no rows")

    metrics = None
    for candidate in [pack_dir / "metrics.json", pack_dir / "metrics_baseline_v052_2.json"]:
        if candidate.is_file():
            metrics = candidate
            break
    if metrics is None:
        fallback = sorted(
            (p for p in pack_dir.glob("metrics_baseline*.json") if p.is_file()),
            key=lambda p: (p.stat().st_mtime, p.name),
            reverse=True,
        )
        metrics = fallback[0] if fallback else None

    if metrics is None:
        errs.append("missing metrics.json or metrics_baseline*.json")
    elif metrics.name == "summary.json":
        errs.append("unexpected summary.json selected as metrics file")

    summary = pack_dir / "summary.json"
    if summary.is_file():
        try:
            summary_doc = json.loads(summary.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errs.append(f"summary.json invalid JSON: {exc}")
        else:
            for key in ("dict_a_count", "dict_b_count", "dict_c_count", "links_count"):
                if key in summary_doc:
                    jsonl_name = key.replace("_count", ".jsonl")
                    jsonl_path = pack_dir / jsonl_name
                    if jsonl_path.is_file():
                        count = sum(1 for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip())
                        if int(summary_doc[key]) != count:
                            errs.append(f"{summary.name} {key}={summary_doc[key]} != {jsonl_name} line_count={count}")

    return errs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "packs",
        nargs="*",
        default=["v0_6_0_clr_v052_4", "v0_6_0_clr_v052_5"],
        help="Pack directory names under assets/calibration/dicts/",
    )
    args = parser.parse_args()

    failures: list[str] = []
    for pack_name in args.packs:
        pack_dir = Path(pack_name)
        if not pack_dir.is_absolute():
            pack_dir = REPO / "assets" / "calibration" / "dicts" / pack_name
        if not pack_dir.is_dir():
            failures.append(f"{pack_dir}: missing directory")
            continue
        errs = _check_pack(pack_dir)
        if errs:
            failures.append(f"{pack_dir}: " + "; ".join(errs))

    if failures:
        for msg in failures:
            print(f"FAIL {msg}", file=sys.stderr)
        return 1

    for pack_name in args.packs:
        pack_dir = Path(pack_name)
        if not pack_dir.is_absolute():
            pack_dir = REPO / "assets" / "calibration" / "dicts" / pack_name
        print(f"PASS {pack_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
