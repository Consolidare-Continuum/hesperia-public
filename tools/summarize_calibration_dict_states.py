#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Aggregate row counts and categorical field value counts for sealed calibration dicts."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

# Fields to tally when present (per-file semantics differ).
_FIELDS_A = ("match_type", "language", "version")
_FIELDS_B = ("status", "version")
_FIELDS_C = ("status", "match_type", "token_count", "language", "version")
_FIELDS_LINKS = ("status", "match_type", "source_dict", "base_weight", "version")


def _count_file(path: Path, fields: tuple[str, ...]) -> dict[str, Any]:
    if not path.is_file():
        return {"absent": True}
    rows = 0
    by_field: dict[str, Counter[str]] = defaultdict(Counter)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        rows += 1
        for k in fields:
            if k in o:
                v = o[k]
                by_field[k][str(v)] += 1
    out: dict[str, Any] = {
        "rows": rows,
        "by_field": {k: dict(sorted(v.items())) for k, v in sorted(by_field.items())},
    }
    if path.name == "dict_a.jsonl":
        out["notes"] = {
            "status": "dict_a v0.6.0 schema has no `status` field; rows are not lifecycle-tagged in JSONL",
        }
    return out


def summarize_version(vdir: Path) -> dict[str, Any]:
    return {
        "dict_a.jsonl": _count_file(vdir / "dict_a.jsonl", _FIELDS_A),
        "dict_b.jsonl": _count_file(vdir / "dict_b.jsonl", _FIELDS_B),
        "dict_c.jsonl": _count_file(vdir / "dict_c.jsonl", _FIELDS_C),
        "links.jsonl": _count_file(vdir / "links.jsonl", _FIELDS_LINKS),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dicts-root",
        type=Path,
        default=REPO / "assets" / "calibration" / "dicts",
    )
    ap.add_argument(
        "--versions",
        nargs="*",
        default=[
            "v0_6_0_clr_v052_5",
            "v0_6_0_clr_v052_4",
            "v0_6_0_clr_v052_3",
            "v0_6_0_clr_v052_2",
            "v0_tfp_cal_wave_002",
        ],
        help="Subdir names under dicts/ (default: v052_4, v052_3, v052_2, wave_002).",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO / "assets" / "artifacts" / "calibration" / "dict_states_snapshot.json",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print JSON to stdout (still writes --out).",
    )
    args = ap.parse_args()

    root = args.dicts_root.resolve()
    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dicts_root": str(root),
        "versions": {},
    }
    for name in args.versions:
        vd = root / name
        if not vd.is_dir():
            payload["versions"][name] = {"error": "directory missing", "path": str(vd)}
            continue
        payload["versions"][name] = summarize_version(vd)

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote: {args.out}", file=sys.stderr)
    if not args.quiet:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
