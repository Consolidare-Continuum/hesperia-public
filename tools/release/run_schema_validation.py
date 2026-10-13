#!/usr/bin/env python3
# HESPERIA — Task 6: full audit includes schema validation — this runs the unified builder.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def main() -> int:
    script = _REPO / "tools" / "release" / "build_release_audit_v0_5_0.py"
    print(
        "Note: schema validation is embedded in build_release_audit_v0_5_0.py → schema_validation_report.json",
        file=sys.stderr,
    )
    return subprocess.call([sys.executable, str(script)] + sys.argv[1:], cwd=str(_REPO))


if __name__ == "__main__":
    raise SystemExit(main())
