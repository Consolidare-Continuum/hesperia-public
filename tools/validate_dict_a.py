#!/usr/bin/env python3
"""Validate DLCR Dict A resources against schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


REPO = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO / "assets" / "schemas" / "lexical_concept" / "dict_a.schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _iter_entries(path: Path):
    if path.suffix.lower() == ".jsonl":
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            yield f"{path}:{line_no}", json.loads(line)
        return

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        for idx, entry in enumerate(payload):
            yield f"{path}[{idx}]", entry
        return
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        for idx, entry in enumerate(payload["entries"]):
            yield f"{path}.entries[{idx}]", entry
        return
    raise ValueError(f"Unsupported Dict A payload format: {path}")


def validate_file(path: Path) -> list[str]:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for location, entry in _iter_entries(path):
        for err in validator.iter_errors(entry):
            where = ".".join(str(x) for x in err.path) or "<root>"
            errors.append(f"{location} {where}: {err.message}")
        cids = entry.get("candidate_concept_ids") or []
        neg = entry.get("negative_patterns") or []
        if not cids and not (isinstance(neg, list) and len(neg) > 0):
            errors.append(
                f"{location} candidate_concept_ids: empty requires non-empty negative_patterns (blocking entry)"
            )
    return errors


def _default_paths() -> list[Path]:
    base = REPO / "assets" / "data" / "engine_dynamics_v060" / "dict_a"
    return sorted(base.glob("*.jsonl"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate DLCR Dict A file(s). With no paths, validates all *.jsonl under dict_a/."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Path(s) to JSON/JSONL Dict A resource (default: pinned pack under engine_dynamics_v060/dict_a/)",
    )
    args = parser.parse_args()
    paths = list(args.paths) if args.paths else _default_paths()
    if not paths:
        print("ERROR: no Dict A files found (expected *.jsonl under assets/data/engine_dynamics_v060/dict_a/)")
        return 2

    all_errors: list[str] = []
    for p in paths:
        if not p.exists():
            print(f"ERROR: file not found: {p}")
            return 2
        try:
            all_errors.extend(validate_file(p))
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {p}: {exc}")
            return 2

    if all_errors:
        for item in all_errors:
            print(f"ERROR: {item}")
        print(f"\nDict A validation failed: {len(all_errors)} error(s)")
        return 1

    print(f"Dict A validation OK ({len(paths)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())

