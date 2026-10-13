# HESPERIA — hesperia-dev-test CLI. Copyright © 2026 igareosh.com.
"""Usage:

    python -m tools.hesperia_dev_test run [--live http://127.0.0.1:8000] [--out PATH]

Default (no --live): in-process TestClient, fast, no server required.
--live: real HTTP round trip against a running uvicorn server, for actual API-speed measurement.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.hesperia_dev_test.runner import print_summary, run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hesperia-dev-test")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="Run the full synthetic battery")
    run_p.add_argument("--live", dest="live", default=None, help="Live API base URL, e.g. http://127.0.0.1:8000")
    run_p.add_argument("--out", dest="out", default=None, help="Report JSON output path")
    run_p.add_argument(
        "--full",
        dest="full",
        action="store_true",
        help="Full-corpus soak (digit/bool/index/diacritic lanes too) instead of bench0_latin only",
    )
    args = parser.parse_args(argv)

    if args.cmd != "run":
        return 1

    out_path = (
        Path(args.out)
        if args.out
        else REPO
        / "outputs"
        / "reports"
        / "hesperia_dev_test"
        / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    report = run(live_base_url=args.live, out_path=out_path, full=args.full)
    print_summary(report)
    print(f"report written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
