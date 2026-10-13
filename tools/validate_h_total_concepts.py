#!/usr/bin/env python3
# HESPERIA — Validate h_total_concepts.json (schema + symmetry + bounds).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_PATH = (
    REPO_ROOT
    / "assets"
    / "data"
    / "engine_dynamics_v060"
    / "semantic_dynamics"
    / "h_total_concepts.json"
)
SCHEMA_PATH = REPO_ROOT / "assets" / "schemas" / "semantic_dynamics" / "h_total_concepts.schema.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate H_total sparse operator JSON.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_PATH,
        help="Path to h_total_concepts.json",
    )
    parser.add_argument(
        "--no-schema",
        action="store_true",
        help="Skip jsonschema validation (symmetry/bounds only).",
    )
    args = parser.parse_args()
    path: Path = args.path
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    data = json.loads(path.read_text(encoding="utf-8"))
    if not args.no_schema:
        try:
            import jsonschema
        except ImportError:
            print("warning: jsonschema not installed; use --no-schema or pip install jsonschema", file=sys.stderr)
            return 3
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(instance=data, schema=schema)

    from hesperia.nlp.semantic_state_update import validate_h_total_symmetry_and_bounds

    sym_ok, bnd_ok, detail = validate_h_total_symmetry_and_bounds(data)
    print(
        json.dumps(
            {
                "path": str(path),
                "symmetric_check_passed": sym_ok,
                "bounded_check_passed": bnd_ok,
                **detail,
            },
            indent=2,
        )
    )
    return 0 if sym_ok and bnd_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
