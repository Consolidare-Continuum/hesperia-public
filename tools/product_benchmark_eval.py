#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from hesperia.product.service import run_product_profile


def _run_set(path: Path, profile: str, expected_key: str) -> dict[str, Any]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    total = len(rows)
    ok = 0
    outputs = []
    for row in rows:
        out = run_product_profile(str(row["text"]), profile)
        outputs.append(out)
        if out.get("status") == "ok" and out.get(expected_key) == row.get(f"expected_{expected_key}"):
            ok += 1
    consistency = len({json.dumps(o, sort_keys=True) for o in outputs}) / max(1, len(outputs))
    return {"total": total, "matched": ok, "accuracy": (ok / max(1, total)), "consistency_ratio": consistency}


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate product benchmark sets.")
    ap.add_argument("--fixtures-dir", default="tests/fixtures/product_benchmarks")
    ap.add_argument("--out", default="product_benchmark_report.json")
    args = ap.parse_args()
    d = Path(args.fixtures_dir)
    report = {
        "llm_audit": _run_set(d / "llm_audit.json", "llm_audit", "risk"),
        "tfp_analysis": _run_set(d / "tfp_analysis.json", "tfp_analysis", "pattern"),
        "document_fingerprint": _run_set(d / "document_fingerprint.json", "document_fingerprint", "pattern"),
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

