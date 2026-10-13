#!/usr/bin/env python3
"""Batch runner with per-run isolation and summary report."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path

from core.engine.pipeline_runner import run_pipeline


def _run_file(path: Path, config: Path) -> tuple[str, dict]:
    text = path.read_text(encoding="utf-8")
    dossier = run_pipeline(text, config_path=config)
    return path.name, dossier


def main() -> int:
    ap = argparse.ArgumentParser(description="Run batch deterministic pipeline over input dir.")
    ap.add_argument("inputs_dir")
    ap.add_argument("--config", required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", default="batch_report.json")
    args = ap.parse_args()
    d = Path(args.inputs_dir)
    files = sorted([p for p in d.iterdir() if p.is_file()])
    config = Path(args.config)
    results: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [ex.submit(_run_file, p, config) for p in files]
        for f in concurrent.futures.as_completed(futs):
            name, dossier = f.result()
            results[name] = dossier
    out = {
        "count": len(results),
        "hashes": {k: dict(v.get("meta", {}).get("run_manifest", {}).get("hashes", {})) for k, v in results.items()},
        "runs": results,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

