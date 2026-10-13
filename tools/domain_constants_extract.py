#!/usr/bin/env python3
# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Domain Constants Extractor (Task 1).
Load reference domain graph from JSON, compute domain_node_count, domain_degree_p95, domain_distance_p95, write frozen constants.
Usage: python3 -m tools.domain_constants_extract --graph path/to/domain_graph.json [--out path/to/domain_constants.json]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

DEFAULT_GRAPH = _REPO / "assets" / "data" / "domain_graph.json"
DEFAULT_OUT = _REPO / "assets" / "data" / "domain_constants.json"


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="python -m tools.domain_constants_extract",
        description="Compute and freeze domain constants from reference domain graph (Task 1).",
    )
    ap.add_argument(
        "--graph",
        type=Path,
        default=DEFAULT_GRAPH,
        help=f"Path to domain graph JSON (default: {DEFAULT_GRAPH})",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Path to write domain_constants JSON (default: {DEFAULT_OUT})",
    )
    args = ap.parse_args()

    if not args.graph.exists():
        print(f"Error: graph file not found: {args.graph}", file=sys.stderr)
        return 1

    from core.domain import extract_constants, load_domain_graph_from_json
    from core.math.io_deterministic_json import write_json_deterministic

    graph = load_domain_graph_from_json(args.graph)
    constants = extract_constants(graph)
    payload = constants.to_dict()
    write_json_deterministic(args.out, payload)
    print(f"Wrote {args.out}: domain_node_count={constants.domain_node_count}, domain_degree_p95={constants.domain_degree_p95}, domain_distance_p95={constants.domain_distance_p95}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
