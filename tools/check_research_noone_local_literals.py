#!/usr/bin/env python3
# TFP-DATA-T11: Fail if "research/_noone_local" appears outside allowlist (tools + hesperia/modules/tfp + runtime).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import sys
from pathlib import Path

NEEDLE = "research/_noone_local"
REPO = Path(__file__).resolve().parents[1]
ALLOWLIST_FILE = REPO / "tools" / "check_research_noone_local_allowlist.txt"
SCAN_ROOTS = [
    REPO / "tools",
    REPO / "runtime",
    REPO / "hesperia" / "modules" / "tfp",
]
EXTS = {".py", ".sh", ".md", ".yml", ".yaml"}


def load_allowlist() -> set[str]:
    lines: set[str] = set()
    if not ALLOWLIST_FILE.is_file():
        return lines
    for ln in ALLOWLIST_FILE.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        lines.add(s)
    return lines


def main() -> int:
    allow = load_allowlist()
    violations: list[str] = []
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if p.suffix.lower() not in EXTS and p.name not in ("Dockerfile",):
                continue
            if "__pycache__" in p.parts:
                continue
            rel = p.relative_to(REPO).as_posix()
            if rel in allow:
                continue
            # Mirrored corpus trees are data, not policy source.
            if "/hesperia/modules/tfp/data/corpus/" in f"/{rel}/" or "/hesperia/modules/tfp/data/tfp_v1/corpus/" in f"/{rel}/":
                continue
            if rel == "tools/check_research_noone_local_literals.py":
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if NEEDLE in text:
                violations.append(rel)
    if violations:
        for v in sorted(violations)[:80]:
            print(f"{v}: contains {NEEDLE!r}", file=sys.stderr)
        print(f"check_research_noone_local_literals: FAIL ({len(violations)} file(s))", file=sys.stderr)
        return 1
    print("check_research_noone_local_literals: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
