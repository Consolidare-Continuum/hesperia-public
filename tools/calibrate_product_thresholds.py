#!/usr/bin/env python3
"""Calibrate LOW/MEDIUM/HIGH thresholds from corpus outputs."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import median

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.engine.pipeline_runner import run_pipeline


def _quantiles(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.3, 0.7
    vals = sorted(values)
    q1 = vals[max(0, int(len(vals) * 0.33) - 1)]
    q2 = vals[max(0, int(len(vals) * 0.66) - 1)]
    return float(q1), float(q2)


def _corr(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2 or len(ys) < 2:
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0.0 or deny == 0.0:
        return 0.0
    return num / (denx * deny)


def main() -> int:
    ap = argparse.ArgumentParser(description="Calibrate product thresholds from corpus.")
    ap.add_argument("corpus_dir")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="product_thresholds_report.json")
    args = ap.parse_args()

    config = Path(args.config)
    files = sorted([p for p in Path(args.corpus_dir).iterdir() if p.is_file()])
    tensions: list[float] = []
    stabilities: list[float] = []
    lengths: list[float] = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        d = run_pipeline(text, config_path=config)
        m = dict(d.get("metrics") or {})
        tensions.append(float(m.get("tension", 0.0)))
        stabilities.append(float(m.get("stability", 0.0)))
        lengths.append(float(len(text)))

    t_low, t_high = _quantiles(tensions)
    s_low, s_high = _quantiles(stabilities)
    report = {
        "samples": len(files),
        "thresholds": {
            "tension": {"low": t_low, "high": t_high},
            "stability": {"low": s_low, "high": s_high},
        },
        "length_bias": {
            "corr_len_tension": _corr(lengths, tensions),
            "corr_len_stability": _corr(lengths, stabilities),
            "median_length": median(lengths) if lengths else 0.0,
        },
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

