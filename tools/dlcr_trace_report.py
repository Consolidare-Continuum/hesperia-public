#!/usr/bin/env python3
"""Build a compact human-readable DLCR report from the gold regression corpus.

For **full pipeline JSON** on arbitrary text, use `tools/dump_dlcr_trace.py` (Ethan PO-10).
This script only summarizes `corpora/gold_spans.jsonl` into `outputs/dlcr_trace_report.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "outputs" / "dlcr_trace_report.md"
GOLD = REPO / "assets" / "data" / "engine_dynamics_v060" / "corpora" / "gold_spans.jsonl"


def main() -> int:
    rows = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line.strip()]
    lines = ["# DLCR Trace Report", ""]
    for idx, row in enumerate(rows, start=1):
        lines.append(f"## Case {idx}")
        lines.append(f"- Text: `{row['text']}`")
        for span in row["spans"]:
            lines.append(f"- Span `{span['span']}` -> expected `{span['winner']}`")
        lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

