#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Release-only CLI for one ledger-bound CORE-D2 candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.dict_calibration.release_freeze import freeze_core_candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Materialize and atomically freeze a CORE-D2 manifest-v2 candidate."
    )
    parser.add_argument("--producer-dir", required=True)
    parser.add_argument("--generation-ledger", required=True)
    parser.add_argument("--generation-ledger-sha256", required=True)
    parser.add_argument("--evaluation-metrics", required=True)
    parser.add_argument("--destination", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = freeze_core_candidate(
        producer_dir=Path(args.producer_dir),
        generation_ledger=Path(args.generation_ledger),
        expected_ledger_sha256=args.generation_ledger_sha256,
        evaluation_metrics=Path(args.evaluation_metrics),
        destination=Path(args.destination),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
