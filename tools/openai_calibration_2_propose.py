#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
OpenAI calibration — **run 2**: LLM map normalized lexicals → Dict B concept drafts.

Requires ``<workdir>/dict_a_normalized.jsonl`` (from ``openai_calibration_1_normalize.py``).
Writes ``<workdir>/dict_b_draft.jsonl``.

Env: same as run 1 (``OPENAI_API_KEY``, ``HESPERIA_CALIB_OPENAI_MODEL``, mock flag).

Example::

  PYTHONPATH=. python3 tools/openai_calibration_2_propose.py \\
    --workdir outputs/dict_calibration/my_run \\
    --limit 120
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.dict_calibration.openai_json import calib_mock_openai, require_openai_key  # noqa: E402
from tools.dict_calibration.run_pipeline import cmd_propose  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--workdir",
        type=Path,
        required=True,
        help="Directory with dict_a_normalized.jsonl",
    )
    ap.add_argument(
        "--dict-b",
        nargs="*",
        default=None,
        help="Override Dict B jsonl paths (default: engine_dynamics_v060 merge)",
    )
    ap.add_argument("--limit", type=int, default=0, help="Cap normalized rows (0 = all)")
    ap.add_argument("--max-concepts", type=int, default=80, help="Cap concepts per batch response")
    ap.add_argument("--catalog-limit", type=int, default=400, help="Dict B lines in prompt")
    ap.add_argument("--propose-batch-size", type=int, default=40)
    ap.add_argument("--dry-run", action="store_true", help="No OpenAI; single placeholder draft if any rows")
    args = ap.parse_args()

    w = args.workdir.resolve()
    norm = w / "dict_a_normalized.jsonl"
    if not norm.is_file():
        print(f"ERROR: missing {norm}; run openai_calibration_1_normalize.py first.", file=sys.stderr)
        return 2

    if not args.dry_run and not calib_mock_openai():
        require_openai_key()

    cmd_propose(
        argparse.Namespace(
            workdir=str(w),
            dict_b=args.dict_b,
            limit=int(args.limit) if args.limit else 0,
            max_concepts=args.max_concepts,
            catalog_limit=args.catalog_limit,
            propose_batch_size=args.propose_batch_size,
            dry_run=args.dry_run,
        )
    )
    print(str(w / "dict_b_draft.jsonl"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
