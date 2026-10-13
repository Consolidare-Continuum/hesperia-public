#!/usr/bin/env python3
# HESPERIA — RAD. Dump full DLCR pipeline JSON for debugging (Ethan PO-10).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Write bounded DLCR trace to stdout or file (no public schema guard)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Dump run_dlcr_pipeline JSON (internal instrumentation).")
    p.add_argument("text", nargs="?", default="", help="Input text (or read stdin if empty)")
    p.add_argument("--out", type=Path, help="Write JSON to file")
    p.add_argument("--max-json-chars", type=int, default=400_000, help="Truncate large JSON string")
    p.add_argument("--mode", default="clinical_speech", help="DLCR mode string")
    args = p.parse_args()
    text = args.text
    if not text.strip():
        text = sys.stdin.read()
    text = (text or "").strip()
    if not text:
        print("ERROR: empty text", file=sys.stderr)
        return 2

    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo))
    from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

    out = run_dlcr_pipeline(text, repo_root=repo, mode=args.mode)
    js = json.dumps(out, indent=2)
    if len(js) > args.max_json_chars:
        js = js[: args.max_json_chars] + "\n… truncated …\n"
    if args.out:
        args.out.write_text(js, encoding="utf-8")
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(js)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
