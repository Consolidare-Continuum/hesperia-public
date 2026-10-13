#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
C-layer language correction: retag ``dict_c.language`` from script (ru/en/mixed), seal new version dir.

Copies ``dict_a.jsonl`` unchanged; ``dict_b`` / ``dict_c`` / ``links`` get ``version`` bumped.
Does not change ``normalized_form``, weights, or matcher code.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.lexical.text_lang import retag_language_field_for_phrase

SRC_VER = "v0_6_0_clr_v052_4"
DST_VER = "v0_6_0_clr_v052_5"


def _rewrite_dict_b(path: Path, old_v: str, new_v: str) -> None:
    lines_out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o: dict[str, Any] = json.loads(line)
        if str(o.get("version", "")) == old_v:
            o["version"] = new_v
        lines_out.append(json.dumps(o, ensure_ascii=False))
    path.write_text("\n".join(lines_out) + "\n", encoding="utf-8")


def _retag_dict_c(path: Path, old_v: str, new_v: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    lines_out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        nf = str(o.get("normalized_form") or "")
        o["language"] = retag_language_field_for_phrase(nf)
        counts[o["language"]] = counts.get(o["language"], 0) + 1
        if str(o.get("version", "")) == old_v:
            o["version"] = new_v
        lines_out.append(json.dumps(o, ensure_ascii=False))
    path.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    return counts


def _rewrite_links_version(path: Path, old_v: str, new_v: str) -> None:
    lines_out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        if str(o.get("version", "")) == old_v:
            o["version"] = new_v
        lines_out.append(json.dumps(o, ensure_ascii=False))
    path.write_text("\n".join(lines_out) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=SRC_VER)
    ap.add_argument("--dst", default=DST_VER)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base = REPO / "assets" / "calibration" / "dicts"
    src = base / args.src
    dst = base / args.dst
    if not (src / "dict_c.jsonl").is_file():
        print(f"ERROR: missing {src / 'dict_c.jsonl'}", file=sys.stderr)
        return 2

    old_v, new_v = args.src, args.dst
    if args.dry_run:
        print(json.dumps({"src": str(src), "dst": str(dst), "old_v": old_v, "new_v": new_v}, indent=2))
        return 0

    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "dict_a.jsonl", dst / "dict_a.jsonl")
    shutil.copy2(src / "dict_b.jsonl", dst / "dict_b.jsonl")
    _rewrite_dict_b(dst / "dict_b.jsonl", old_v, new_v)

    shutil.copy2(src / "dict_c.jsonl", dst / "dict_c.jsonl")
    c_counts = _retag_dict_c(dst / "dict_c.jsonl", old_v, new_v)

    shutil.copy2(src / "links.jsonl", dst / "links.jsonl")
    _rewrite_links_version(dst / "links.jsonl", old_v, new_v)

    for name in ("summary.json", "metrics_baseline_v052_2.json"):
        p = src / name
        if p.is_file():
            shutil.copy2(p, dst / name)

    summary = {
        "run": "c_layer_language_retag_v1",
        "source_version": old_v,
        "output_version": new_v,
        "dict_c_language_counts_after_retag": c_counts,
        "note": "dict_c.language only; matcher unchanged; audit/future routing alignment",
    }
    (dst / "summary_language_retag.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
