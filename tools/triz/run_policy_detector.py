#!/usr/bin/env python3
"""CLI: Policy Contradiction Detector (HSP-TRIZ-P1)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus", type=Path, required=True, help="Benchmark dir with graph.json")
    p.add_argument("--out", type=Path, default=None, help="Write package JSON here")
    args = p.parse_args()

    from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
    from hesperia.product.package_builder import PRODUCT_SKUS, build_policy_package
    from hesperia.product.release_gate import run_release_gate

    spec = json.loads((args.corpus / "graph.json").read_text(encoding="utf-8"))
    triz = run_triz_analysis_complete(
        active_graph_from_payload(spec["active_graph"]),
        spec.get("topology"),
    )
    cid = args.corpus.name
    pkg = build_policy_package(triz, cid)
    gate = run_release_gate()
    print(f"Product: {PRODUCT_SKUS['policy_detector']}")
    print(f"Corpus: {cid}")
    print(f"Global tension score: {pkg['report']['global_tension_score']:.2f}")
    print(f"Conflict cluster count: {len(pkg['report']['top_conflict_clusters'])}")
    print(f"Export bundle: OK")
    print(f"Readiness gate: {'PASS' if gate.passed else 'FAIL'}")
    if args.out:
        args.out.write_text(json.dumps(pkg, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
