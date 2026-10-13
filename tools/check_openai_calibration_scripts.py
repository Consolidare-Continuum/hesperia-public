#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Smoke-check OpenAI calibration CLIs: --help, imports, stderr logging."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_CALIBRATION_DIR = REPO_ROOT / "tools" / "openai_calibration"

SCRIPTS = (
    "openai_calibrate_dict_a.py",
    "openai_calibrate_areas.py",
    "openai_calibrate_topology.py",
    "openai_calibration_audit.py",
)


def main() -> int:
    failed = False
    for name in SCRIPTS:
        path = _CALIBRATION_DIR / name
        if not path.is_file():
            print(f"FAIL missing {path}", file=sys.stderr)
            failed = True
            continue
        proc = subprocess.run(
            [sys.executable, str(path), "--help"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            print(f"FAIL {name} --help exit={proc.returncode}", file=sys.stderr)
            if proc.stderr:
                print(proc.stderr, file=sys.stderr)
            failed = True
        else:
            out = (proc.stdout or "") + (proc.stderr or "")
            if name != "openai_calibration_audit.py" and "--limit" not in out:
                print(f"WARN {name} --help has no --limit in text", file=sys.stderr)
            if name != "openai_calibration_audit.py" and "--progress-every" not in out:
                print(f"WARN {name} --help has no --progress-every in text", file=sys.stderr)
            print(f"OK {name} --help")

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from tools.openai_calibration.openai_calibration_utils import log_stderr, log_tool_banner, log_tool_progress; "
            "log_tool_banner('check', x=1); log_tool_progress('check', 1, 3, every=1, detail='t'); "
            "log_stderr('[check] ok')",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        print(f"FAIL openai_calibration_utils log helpers: {proc.stderr}", file=sys.stderr)
        failed = True
    else:
        print("OK openai_calibration_utils log helpers")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
