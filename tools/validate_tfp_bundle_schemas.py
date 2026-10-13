#!/usr/bin/env python3
# HESPERIA — RAD. Validate TFP file pipeline artifacts (Task 9 subset).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO / "assets" / "schemas" / "tfp_bundle"

ARTIFACTS = [
    ("01_structural_batch.json", "01_structural_batch.schema.json"),
    ("10_calibration_audit.json", "10_calibration_audit.schema.json"),
    ("11_calibration_release_gate.json", "11_calibration_release_gate.schema.json"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate bundle JSON against schemas/tfp_bundle/*.schema.json")
    ap.add_argument("--bundle-dir", type=Path, required=True)
    args = ap.parse_args()
    bd = args.bundle_dir.resolve()
    errs: list[str] = []
    for data_name, schema_name in ARTIFACTS:
        data_path = bd / data_name
        if not data_path.is_file():
            continue
        schema_path = SCHEMA_DIR / schema_name
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        instance = json.loads(data_path.read_text(encoding="utf-8"))
        v = Draft202012Validator(schema)
        for e in v.iter_errors(instance):
            errs.append(f"{data_name}: {'/'.join(str(x) for x in e.path)}: {e.message}")
    if errs:
        for e in errs[:80]:
            print(e, file=sys.stderr)
        print(f"validate_tfp_bundle_schemas: FAIL ({len(errs)} error(s))", file=sys.stderr)
        return 1
    print("validate_tfp_bundle_schemas: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
