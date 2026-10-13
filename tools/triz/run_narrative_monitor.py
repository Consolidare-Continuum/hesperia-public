#!/usr/bin/env python3
"""CLI: Narrative Monitor (HSP-TRIZ-N1)."""
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
    from hesperia.product.package_builder import PRODUCT_SKUS, build_narrative_package
    from hesperia.product.release_gate import run_release_gate

    spec = json.loads((args.corpus / "graph.json").read_text(encoding="utf-8"))
    triz = run_triz_analysis_complete(
        active_graph_from_payload(spec["active_graph"]),
        spec.get("topology"),
    )
    pkg = build_narrative_package(triz, args.corpus.name)
    gate = run_release_gate()
    n0 = pkg["report"]["narratives"][0] if pkg["report"]["narratives"] else {}
    print(f"Product: {PRODUCT_SKUS['narrative_monitor']}")
    print(f"Penetration: {float(n0.get('penetration', 0)):.2f}")
    print(f"Routes: {len(pkg['report']['top_routes'])}")
    print(f"Readiness gate: {'PASS' if gate.passed else 'FAIL'}")
    if args.out:
        args.out.write_text(json.dumps(pkg, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
