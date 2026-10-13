#!/usr/bin/env python3
# HESPERIA — Task 6: recompute release/v0.5.0/checksums.txt only.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def main() -> int:
    script = _REPO / "tools" / "release" / "build_release_audit_v0_5_0.py"
    return subprocess.call(
        [sys.executable, str(script), "--checksums-only"] + sys.argv[1:],
        cwd=str(_REPO),
    )


if __name__ == "__main__":
    raise SystemExit(main())
