#!/usr/bin/env python3
"""Minimal module test harness."""

from __future__ import annotations

import argparse
from pathlib import Path

from core.engine.context_schema import validate_context
from core.engine.core import HesperiaEngine
from core.engine.module_loader import resolve_module_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Run minimal module contract test.")
    ap.add_argument("module", help="Module alias or import path, e.g. tfp or hesperia.modules.tfp.module")
    args = ap.parse_args()

    engine = HesperiaEngine()
    config_path = Path(__file__).resolve().parents[1] / "assets" / "config" / "pipeline.yaml"
    engine.load_from_config(config_path)
    resolved = resolve_module_path(args.module)
    target = [m for m in engine.modules if m.name == args.module or engine._module_paths.get(m.name) in {args.module, resolved}]
    if not target:
        raise ValueError(f"module_not_in_pipeline:{args.module}")
    ctx = engine.run("module harness smoke input", signals=[{"family_id": 1, "strength": 0.2, "source": "harness"}])
    validate_context(ctx, "harness")
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

