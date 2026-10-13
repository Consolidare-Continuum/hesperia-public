#!/usr/bin/env python3
"""Fail when core imports module internals directly."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

FORBIDDEN_PREFIX = "hesperia.modules."
ALLOWED_FILES = {
    "core/engine/core.py",
}
SCAN_DIRS = (
    "core",
    "hesperia/engine",
)


def _violations_in_file(path: Path, repo_root: Path) -> list[tuple[int, str]]:
    rel = path.relative_to(repo_root).as_posix()
    if rel in ALLOWED_FILES:
        return []
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name
                if mod.startswith(FORBIDDEN_PREFIX):
                    out.append((node.lineno, f"forbidden import {mod}"))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith(FORBIDDEN_PREFIX):
                out.append((node.lineno, f"forbidden from {mod}"))
    return out


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    violations: list[tuple[str, int, str]] = []
    for base in SCAN_DIRS:
        d = repo_root / base
        if not d.exists():
            continue
        for py in d.rglob("*.py"):
            for line, msg in _violations_in_file(py, repo_root):
                violations.append((py.relative_to(repo_root).as_posix(), line, msg))
    if violations:
        for rel, line, msg in violations[:200]:
            print(f"{rel}:{line}: {msg}")
        print(f"Total core/module boundary violations: {len(violations)}", file=sys.stderr)
        return 1
    print("Core/module boundary check: no violations.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

