#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
OpenAI calibration — **run 1**: LLM-normalize lexical candidates.

Writes ``<workdir>/dict_a_normalized.jsonl`` (requires ``dict_a_candidates.jsonl`` unless ``--corpus`` is passed).

Env: ``OPENAI_API_KEY``; ``HESPERIA_CALIB_OPENAI_MODEL`` (default ``gpt-4o-mini``);
``HESPERIA_CALIB_MOCK_OPENAI=1`` skips the network (deterministic stub).

Example::

  PYTHONPATH=. python3 tools/openai_calibration_1_normalize.py \\
    --workdir outputs/dict_calibration/my_run \\
    --corpus research/_noone_local/2_cleaned

If candidates already exist, omit ``--corpus``::

  PYTHONPATH=. python3 tools/openai_calibration_1_normalize.py --workdir outputs/dict_calibration/my_run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.dict_calibration.openai_json import calib_mock_openai, require_openai_key  # noqa: E402
from tools.dict_calibration.run_pipeline import cmd_extract, cmd_normalize  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--workdir",
        type=Path,
        required=True,
        help="Directory for dict_a_candidates.jsonl / dict_a_normalized.jsonl",
    )
    ap.add_argument(
        "--corpus",
        type=Path,
        default=None,
        help="If dict_a_candidates.jsonl is missing, run extract from this corpus dir first",
    )
    ap.add_argument("--min-freq", type=int, default=2, help="extract: min phrase frequency")
    ap.add_argument("--batch-size", type=int, default=24, help="OpenAI: rows per completion")
    ap.add_argument(
        "--max-llm-rows",
        type=int,
        default=None,
        help="Cap rows sent to API (freq-sorted); default = all",
    )
    ap.add_argument("--dry-run", action="store_true", help="No OpenAI; identity normalization")
    args = ap.parse_args()

    w = args.workdir.resolve()
    w.mkdir(parents=True, exist_ok=True)
    cand = w / "dict_a_candidates.jsonl"

    if not cand.is_file():
        if args.corpus is None:
            print(
                f"ERROR: missing {cand}; pass --corpus to extract first.",
                file=sys.stderr,
            )
            return 2
        cmd_extract(
            argparse.Namespace(corpus=str(args.corpus.resolve()), out=str(w), min_freq=args.min_freq)
        )

    if not args.dry_run and not calib_mock_openai():
        require_openai_key()

    cmd_normalize(
        argparse.Namespace(
            workdir=str(w),
            batch_size=args.batch_size,
            max_llm_rows=args.max_llm_rows,
            dry_run=args.dry_run,
            wave_slice_index=None,
            wave_slice_total=None,
        )
    )
    print(str(w / "dict_a_normalized.jsonl"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
