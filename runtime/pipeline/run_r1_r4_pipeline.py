#!/usr/bin/env python3

# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Run R1–R4 pipeline: segment text at R1–R4 → L1–L9 → Unit → BookProfile.
Usage: python3 -m runtime.pipeline.run_r1_r4_pipeline [--text "..." | --file path] [--book-id id] [--out-dir dir] [--levels R1,R2,R3,R4] [--validate]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE.parents[1]) not in sys.path:
    sys.path.insert(0, str(_HERE.parents[1]))

from runtime.pipeline.r1_r4_pipeline import run_full_pipeline_to_json


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Run R1–R4 pipeline; output Units + BookProfile JSON.")
    ap.add_argument("--text", default=None, help="Input text (default: short sample)")
    ap.add_argument("--file", type=Path, default=None, help="Read input from file")
    ap.add_argument("--book-id", default="book", help="book_id for BookProfile")
    ap.add_argument("--out-dir", type=Path, default=None, help="Write units.json and book_profile.json here")
    ap.add_argument("--out-units-jsonl", type=Path, default=None, help="Also write units as one JSON object per line (safe for streaming/head; avoid large single JSON in context)")
    ap.add_argument("--levels", default="R1,R2,R3,R4", help="Comma-separated levels (default: R1,R2,R3,R4)")
    ap.add_argument("--validate", action="store_true", help="Validate outputs against Part C schemas (requires jsonschema)")
    args = ap.parse_args()

    if args.file and args.file.exists():
        text = args.file.read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = "Justice and fairness support social order. Harm and conflict reduce trust. Cooperation builds stability."

    levels = [x.strip() for x in args.levels.split(",") if x.strip()]
    out_units = Path(args.out_dir, "units.json") if args.out_dir else None
    out_profile = Path(args.out_dir, "book_profile.json") if args.out_dir else None
    out_units_jsonl = args.out_units_jsonl

    result = run_full_pipeline_to_json(
        text,
        book_id=args.book_id,
        levels=levels,
        out_units=out_units,
        out_profile=out_profile,
        out_units_jsonl=out_units_jsonl,
        validate=args.validate,
    )

    if not args.out_dir and sys.stdout.isatty():
        print("Units:", len(result["units"]), file=sys.stderr)
        print("BookProfile.book_id:", result["book_profile"]["book_id"], file=sys.stderr)
        if result.get("validation"):
            v = result["validation"]
            print("Validation units_ok:", v.get("units_ok"), "profile_ok:", v.get("profile_ok"), file=sys.stderr)
    elif not args.out_dir:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
