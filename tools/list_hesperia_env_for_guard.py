#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Emit sorted HESPERIA_* env var names for ALLOWED_HESPERIA_ENV (env_guard).

Patterns: os.environ.get / [], _env_bool, _truthy, _float with string literal keys.
Also adds HESPERIA_RUNTIME_MODE (MODE_ENV in artifact writer).

Run from repo root: python3 tools/list_hesperia_env_for_guard.py
Paste lines into runtime/shipping/env_guard.py ALLOWED_HESPERIA_ENV.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    names: set[str] = set()
    pats = [
        re.compile(r'environ\.get\(\s*["\'](HESPERIA_[A-Z0-9_]+)["\']'),
        re.compile(r'environ\[\s*["\'](HESPERIA_[A-Z0-9_]+)["\']'),
        re.compile(r'_env_bool\(\s*["\'](HESPERIA_[A-Z0-9_]+)["\']'),
        re.compile(r'_truthy\(\s*["\'](HESPERIA_[A-Z0-9_]+)["\']'),
        re.compile(r'_float\(\s*["\'](HESPERIA_[A-Z0-9_]+)["\']'),
    ]
    skip_dir = {".git", "__pycache__"}
    for dp, dirnames, fs in os.walk("."):
        dirnames[:] = [d for d in dirnames if d not in skip_dir]
        for f in fs:
            if not f.endswith(".py"):
                continue
            p = os.path.join(dp, f)
            try:
                t = open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for pat in pats:
                names.update(pat.findall(t))
    wpath = Path("runtime/artifact_writer/writer.py")
    if wpath.is_file() and 'MODE_ENV = "HESPERIA_RUNTIME_MODE"' in wpath.read_text(encoding="utf-8", errors="ignore"):
        names.add("HESPERIA_RUNTIME_MODE")
    for n in sorted(names):
        print(f'    "{n}",')
    print(f"# total {len(names)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
