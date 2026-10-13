#!/usr/bin/env python3
# HESPERIA — TFP-ENF-04: fail if calibration metrics.json missing required shape or below floors.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Check metrics.json for TFP/calibration release chain.")
    ap.add_argument(
        "--pack-dir",
        type=Path,
        default=None,
        help="Directory containing metrics.json (default: active calibration pack from env/version)",
    )
    args = ap.parse_args()
    pack = args.pack_dir
    if pack is None:
        ver = os.environ.get("HESPERIA_CALIB_DICT_VERSION", "v0_6_0_clr_v052_2").strip()
        pack = REPO / "assets" / "calibration" / "dicts" / ver
    mp = pack / "metrics.json"
    if not mp.is_file():
        print(f"SKIP: no metrics.json at {mp}", file=sys.stderr)
        return 0
    data = json.loads(mp.read_text(encoding="utf-8"))
    n_texts = int(data.get("n_texts") or 0)
    if n_texts < 1:
        print("FAIL: metrics n_texts < 1", file=sys.stderr)
        return 1
    per = data.get("per_text")
    if not isinstance(per, list) or len(per) < 1:
        print("FAIL: metrics per_text missing or empty", file=sys.stderr)
        return 1
    total_acc = sum(int(x.get("lexical_hits_accepted") or 0) for x in per)
    min_sum = int(os.environ.get("HESPERIA_METRICS_MIN_LEXICAL_ACCEPTED_SUM", "100"))
    if total_acc < min_sum:
        print(f"FAIL: lexical_hits_accepted sum {total_acc} < floor {min_sum}", file=sys.stderr)
        return 1
    non_empty = sum(1 for x in per if int(x.get("lexical_hits_accepted") or 0) > 0)
    ratio = non_empty / float(len(per))
    min_ratio = float(os.environ.get("HESPERIA_METRICS_MIN_PER_TEXT_NON_EMPTY_RATIO", "0.2"))
    if ratio < min_ratio:
        print(
            f"FAIL: per_text_non_empty_ratio {ratio:.4f} < floor {min_ratio}",
            file=sys.stderr,
        )
        return 1
    lowest = min(int(x.get("lexical_hits_accepted") or 0) for x in per)
    min_lowest = int(os.environ.get("HESPERIA_METRICS_MIN_LOWEST_PER_TEXT_ACCEPTED", "300"))
    if lowest < min_lowest:
        print(
            f"FAIL: min per_text lexical_hits_accepted {lowest} < floor {min_lowest}",
            file=sys.stderr,
        )
        return 1
    print(
        f"OK: metrics gate pack={pack} n_texts={n_texts} accepted_sum={total_acc} "
        f"per_text_non_empty_ratio={ratio:.4f} min_per_text_accepted={lowest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
