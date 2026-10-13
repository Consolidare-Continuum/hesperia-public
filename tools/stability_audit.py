#!/usr/bin/env python3
"""Repeatability audit over deterministic pipeline outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.engine.pipeline_runner import run_pipeline


def _entropy(values: list[float]) -> float:
    import math

    s = sum(values)
    if s <= 0:
        return 0.0
    p = [v / s for v in values if v > 0]
    return -sum(x * math.log2(x) for x in p) if p else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Run stability audit for repeated same-input runs.")
    ap.add_argument("input_file")
    ap.add_argument("--config", required=True)
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--out", default="stability_audit.json")
    args = ap.parse_args()

    text = Path(args.input_file).read_text(encoding="utf-8")
    config = Path(args.config)
    dossiers: list[dict[str, Any]] = [run_pipeline(text, config_path=config) for _ in range(max(1, args.runs))]

    tensions = [float((d.get("metrics") or {}).get("tension", 0.0)) for d in dossiers]
    stabilities = [float((d.get("metrics") or {}).get("stability", 0.0)) for d in dossiers]
    area_vectors = [list((d.get("areas") or {}).values()) for d in dossiers]
    entropies = [_entropy([float(x) for x in v]) for v in area_vectors]
    hashes = [dict(d.get("meta") or {}).get("hash_project") for d in dossiers]
    unique_hashes = sorted(set(hashes))

    report = {
        "runs": len(dossiers),
        "stability_delta": max(stabilities) - min(stabilities) if stabilities else 0.0,
        "tension_delta": max(tensions) - min(tensions) if tensions else 0.0,
        "entropy_variance": pstdev(entropies) if len(entropies) > 1 else 0.0,
        "area_vector_variance": pstdev([mean([float(x) for x in v]) for v in area_vectors]) if len(area_vectors) > 1 else 0.0,
        "project_hash_identical": len(unique_hashes) == 1,
        "project_hashes": unique_hashes,
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

