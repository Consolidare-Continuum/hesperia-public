#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""CLI for the frozen core dictionary calibration-pack gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.dict_calibration.core_pack_gate import evaluate_core_pack


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate one frozen core dictionary calibration pack.",
    )
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--limits", type=Path, required=True)
    parser.add_argument(
        "--limits-sha256",
        required=True,
        help="Independent expected SHA-256 digest of the frozen limits file.",
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    verdict = evaluate_core_pack(
        bundle=args.bundle,
        evaluation=args.evaluation,
        limits=args.limits,
        expected_limits_sha256=args.limits_sha256,
        repo_root=args.repo_root,
        require_manifest_v2=True,
    )
    try:
        print(
            json.dumps(
                verdict,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
        )
    except (TypeError, ValueError):
        return 2
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
