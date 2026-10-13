# HESPERIA — CLI for FPF-BUII MCP (python -m sphere.fpf_inspect).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sphere.fpf_inspect.climb import gap_detect, inspect_climb
from sphere.fpf_inspect.map_hesperia_inspect import map_step
from sphere.fpf_inspect.map_hesperia_ops import ops_map_step
from sphere.fpf_inspect.probe import probe


def _load_result(path: str | None, inline_json: str | None) -> dict[str, Any] | None:
    if inline_json:
        data = json.loads(inline_json)
        if not isinstance(data, dict):
            raise SystemExit("analyze JSON must be an object")
        return data
    if path:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise SystemExit("analyze JSON must be an object")
        return data
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sphere.fpf_inspect", description="FPF-BUII dig CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_probe = sub.add_parser("probe", help="Probe one layer")
    p_probe.add_argument("--layer", required=True)
    p_probe.add_argument("--analyze-json", default=None)
    p_probe.add_argument("--analyze-file", default=None)

    p_climb = sub.add_parser("climb", help="Climb layers + GapReport")
    p_climb.add_argument("--analyze-json", default=None)
    p_climb.add_argument("--analyze-file", default=None)
    p_climb.add_argument("--stop-on-first-gap", action="store_true", default=True)
    p_climb.add_argument("--full", action="store_true", help="Do not stop on first gap")
    p_climb.add_argument("--layers", default=None, help="Comma-separated layer ids")

    p_gaps = sub.add_parser("gaps", help="GapReport only (full climb)")
    p_gaps.add_argument("--analyze-json", default=None)
    p_gaps.add_argument("--analyze-file", default=None)

    p_map = sub.add_parser("map-step", help="thinking_map_step on hesperia_inspect")
    p_map.add_argument("--state", default="l0_hash")
    p_map.add_argument("--evidence", default="")
    p_map.add_argument("--task", default="hesperia dig")

    p_ops = sub.add_parser("ops-map-step", help="thinking_map_step on hesperia_ops")
    p_ops.add_argument("--state", default="start")
    p_ops.add_argument("--evidence", default="")
    p_ops.add_argument("--task", default="hesperia roll")

    args = parser.parse_args(argv)

    if args.cmd == "probe":
        result = _load_result(args.analyze_file, args.analyze_json)
        out = probe(args.layer, result)
    elif args.cmd == "climb":
        result = _load_result(args.analyze_file, args.analyze_json)
        layers = tuple(x.strip() for x in args.layers.split(",") if x.strip()) if args.layers else None
        out = inspect_climb(
            result,
            stop_on_first_gap=not args.full,
            layers=layers,
        )
    elif args.cmd == "gaps":
        result = _load_result(args.analyze_file, args.analyze_json)
        out = gap_detect(result)
    elif args.cmd == "map-step":
        out = map_step(current_state=args.state, current_evidence=args.evidence, task=args.task)
    elif args.cmd == "ops-map-step":
        out = ops_map_step(current_state=args.state, current_evidence=args.evidence, task=args.task)
    else:
        return 2

    sys.stdout.write(json.dumps(out, indent=2, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
