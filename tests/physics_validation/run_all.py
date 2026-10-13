#!/usr/bin/env python3
# HESPERIA — run physics validation suite (TASK_6_10 §9).
# Usage: python -m tests.physics_validation.run_all

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    here = Path(__file__).resolve().parent
    return subprocess.call(
        [sys.executable, "-m", "pytest", str(here), "-q", "--tb=short"],
        cwd=str(here.parent.parent),
    )


if __name__ == "__main__":
    raise SystemExit(main())
