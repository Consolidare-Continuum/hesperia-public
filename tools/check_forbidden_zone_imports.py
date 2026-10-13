#!/usr/bin/env python3
# HESPERIA — Block research.* and legacy.* imports in shipping-critical trees.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# research is allowed only in selected runtime/pipeline entrypoints (experimental E2E / TFP file runs).
# legacy must never be imported as a Python package from active code (archive is not on PYTHONPATH by policy).
#
# Usage: python3 tools/check_forbidden_zone_imports.py [--repo PATH]

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# No research.* / legacy.* except where noted.
STRICT_TREES = [
    "runtime/services",
    "runtime/shipping",
    "runtime/api",
    "hesperia/engine",
    "core/engine",
]

PIPELINE_TREE = "runtime/pipeline"
RESEARCH_ALLOWLIST = frozenset(
    {
        "runtime/pipeline/run_e2e_all.py",
        "runtime/pipeline/run_tfp_file_pipeline.py",
    }
)


def _forbidden_module(name: str | None) -> bool:
    if not name or name == "__future__":
        return False
    if name == "research" or name.startswith("research."):
        return True
    if name == "legacy" or name.startswith("legacy."):
        return True
    return False


def _scan_imports(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (lineno, kind, module) for import/from nodes."""
    out: list[tuple[int, str, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    out.append((node.lineno, "import", alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.append((node.lineno, "from", node.module))
    return out


def _check_tree(repo: Path, rel_prefix: str, violations: list[str]) -> None:
    d = repo / rel_prefix
    if not d.is_dir():
        return
    for py in sorted(d.rglob("*.py")):
        if "__pycache__" in str(py):
            continue
        rel = py.relative_to(repo).as_posix()
        for lineno, _kind, mod in _scan_imports(py):
            if not _forbidden_module(mod):
                continue
            violations.append(f"{rel}:{lineno}: forbidden zone import: {mod}")


def _check_pipeline(repo: Path, violations: list[str]) -> None:
    d = repo / PIPELINE_TREE
    if not d.is_dir():
        return
    for py in sorted(d.rglob("*.py")):
        if "__pycache__" in str(py):
            continue
        rel = py.relative_to(repo).as_posix()
        allow_research = rel in RESEARCH_ALLOWLIST
        for lineno, _kind, mod in _scan_imports(py):
            if mod == "legacy" or (mod and mod.startswith("legacy.")):
                violations.append(f"{rel}:{lineno}: legacy import forbidden in runtime/pipeline: {mod}")
                continue
            if mod == "research" or (mod and mod.startswith("research.")):
                if not allow_research:
                    violations.append(f"{rel}:{lineno}: research import forbidden outside allowlist: {mod}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Forbid research/legacy imports in strict trees.")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    repo = args.repo.resolve()
    violations: list[str] = []
    for t in STRICT_TREES:
        _check_tree(repo, t, violations)
    _check_pipeline(repo, violations)
    if violations:
        for v in violations[:120]:
            print(v, file=sys.stderr)
        if len(violations) > 120:
            print(f"... and {len(violations) - 120} more", file=sys.stderr)
        print(f"check_forbidden_zone_imports: FAIL ({len(violations)} violation(s))", file=sys.stderr)
        return 1
    print("check_forbidden_zone_imports: OK (strict trees + runtime/pipeline policy)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
