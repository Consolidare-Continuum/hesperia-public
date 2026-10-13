#!/usr/bin/env python3
"""CLI: Innovation Radar (HSP-TRIZ-I1)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
    from hesperia.product.package_builder import PRODUCT_SKUS, build_innovation_package
    from hesperia.product.release_gate import run_release_gate

    spec = json.loads((args.corpus / "graph.json").read_text(encoding="utf-8"))
    triz = run_triz_analysis_complete(
        active_graph_from_payload(spec["active_graph"]),
        spec.get("topology"),
    )
    pkg = build_innovation_package(triz, args.corpus.name)
    gate = run_release_gate()
    print(f"Product: {PRODUCT_SKUS['innovation_radar']}")
    print(f"Innovation pressure: {pkg['report']['innovation_pressure_score']:.2f}")
    print(f"Strongest clusters: {len(pkg['report']['strongest_clusters'])}")
    print(f"Readiness gate: {'PASS' if gate.passed else 'FAIL'}")
    if args.out:
        args.out.write_text(json.dumps(pkg, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
