#!/usr/bin/env python3
# HESPERIA — Engine may not call core.projection except under core/engine/projection/.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Rationale: single choke point is project_to_public; bypass breaks auditability.
# Usage: python3 tools/check_engine_projection_boundary.py [--repo PATH]

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

_ENGINE_ROOT = Path("core/engine")


def _violations_for_file(repo: Path, py: Path) -> list[str]:
    rel = py.relative_to(repo).as_posix()
    if not rel.startswith("core/engine/"):
        return []
    sub = rel[len("core/engine/") :]
    if sub == "projection" or sub.startswith("projection/"):
        return []
    bad: list[str] = []
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return bad
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name and _is_core_projection(alias.name):
                    bad.append(f"{rel}:{node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if _is_core_projection(node.module):
                bad.append(f"{rel}:{node.lineno}: from {node.module}")
    return bad


def _is_core_projection(mod: str) -> bool:
    return mod == "core.projection" or mod.startswith("core.projection.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Forbid core.projection imports outside core/engine/projection/.")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    repo = args.repo.resolve()
    root = repo / _ENGINE_ROOT
    if not root.is_dir():
        print(f"missing {_ENGINE_ROOT}", file=sys.stderr)
        return 1
    all_bad: list[str] = []
    for py in sorted(root.rglob("*.py")):
        if "__pycache__" in str(py):
            continue
        all_bad.extend(_violations_for_file(repo, py))
    if all_bad:
        for b in all_bad[:80]:
            print(b, file=sys.stderr)
        if len(all_bad) > 80:
            print(f"... and {len(all_bad) - 80} more", file=sys.stderr)
        print(f"check_engine_projection_boundary: FAIL ({len(all_bad)} violation(s))", file=sys.stderr)
        return 1
    print("check_engine_projection_boundary: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
