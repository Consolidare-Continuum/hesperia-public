#!/usr/bin/env python3
# HESPERIA — Find Python modules under engine/core/sphere not reachable from runtime+tests import graph.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Heuristic BFS over static imports. Misses dynamic imports and relative imports in some cases.
# Usage: python3 tools/find_unreferenced_files.py [--repo PATH] [--json]

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import deque
from pathlib import Path

# Repo packages we can resolve to paths (top-level names).
ROOT_PREFIXES = frozenset({"hesperia", "core", "runtime", "sphere", "research"})

SKIP_DIR_PARTS = frozenset(
    {
        "__pycache__",
        ".venv",
        "legacy",
        "node_modules",
        ".git",
    }
)


def _is_skipped(path: Path) -> bool:
    return any(p in SKIP_DIR_PARTS for p in path.parts)


def resolve_module_to_file(repo: Path, mod: str) -> Path | None:
    if not mod or mod.startswith("."):
        return None
    head = mod.split(".", 1)[0]
    if head not in ROOT_PREFIXES:
        return None
    rel = mod.replace(".", "/")
    py = repo / f"{rel}.py"
    if py.is_file():
        return py.resolve()
    init = repo / rel / "__init__.py"
    if init.is_file():
        return init.resolve()
    return None


def _parse_imports(text: str) -> tuple[set[str], set[str]]:
    """Return (import_modules, from_modules)."""
    imods: set[str] = set()
    fmods: set[str] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return imods, fmods
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    imods.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            fmods.add(node.module)
    return imods, fmods


def collect_seed_files(repo: Path, roots: list[str]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        d = repo / root
        if not d.is_dir():
            continue
        for py in d.rglob("*.py"):
            if _is_skipped(py):
                continue
            out.append(py.resolve())
    return out


def bfs_reachable(repo: Path, seeds: list[Path]) -> set[Path]:
    seen: set[Path] = set()
    q: deque[Path] = deque()
    for s in seeds:
        if s.is_file():
            seen.add(s)
            q.append(s)
    while q:
        path = q.popleft()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        imods, fmods = _parse_imports(text)
        for mod in sorted(imods | fmods):
            target = resolve_module_to_file(repo, mod)
            if target and target.is_file() and target not in seen and not _is_skipped(target):
                # stay under repo
                try:
                    target.relative_to(repo.resolve())
                except ValueError:
                    continue
                seen.add(target)
                q.append(target)
    return seen


def compute_unreferenced_relpaths(
    repo: Path,
    *,
    seed_roots: list[str] | None = None,
    scan_roots: list[str] | None = None,
) -> list[str]:
    """Return sorted relative paths of unreferenced .py files (default: runtime+tests → hesperia,core,sphere)."""
    seed_roots = seed_roots or ["runtime", "tests"]
    scan_roots = scan_roots or ["hesperia", "core", "sphere"]
    seeds = collect_seed_files(repo, seed_roots)
    reachable = bfs_reachable(repo, seeds)
    candidates: list[Path] = []
    for pkg in scan_roots:
        candidates.extend(list_package_py(repo, pkg))
    unref: list[Path] = []
    for p in sorted(set(candidates)):
        if p in reachable:
            continue
        unref.append(p)
    return sorted(str(p.relative_to(repo)) for p in unref)


def list_package_py(repo: Path, pkg: str) -> list[Path]:
    d = repo / pkg
    if not d.is_dir():
        return []
    out: list[Path] = []
    for py in d.rglob("*.py"):
        if _is_skipped(py):
            continue
        out.append(py.resolve())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="List .py files under packages not reached from runtime+tests.")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument(
        "--roots",
        default="runtime,tests",
        help="Comma-separated roots for BFS seeds (default: runtime,tests)",
    )
    ap.add_argument(
        "--scan",
        default="hesperia,core,sphere",
        help="Comma-separated trees to report unreferenced files under",
    )
    ap.add_argument("--json", action="store_true", help="Emit JSON array of relative paths")
    ap.add_argument(
        "--count-only",
        action="store_true",
        help="Print only the count of unreferenced files to stdout (no paths)",
    )
    args = ap.parse_args()
    repo = args.repo.resolve()
    seed_roots = [x.strip() for x in args.roots.split(",") if x.strip()]
    scan_roots = [x.strip() for x in args.scan.split(",") if x.strip()]
    rels = compute_unreferenced_relpaths(repo, seed_roots=seed_roots, scan_roots=scan_roots)
    if args.count_only:
        print(len(rels))
        return 0
    if args.json:
        print(json.dumps(rels, indent=2))
        return 0
    seeds = collect_seed_files(repo, seed_roots)
    reachable = bfs_reachable(repo, seeds)
    print(f"find_unreferenced_files: seeds={seed_roots!r} scan={scan_roots!r}", file=sys.stderr)
    print(f"reachable modules (files): {len(reachable)}", file=sys.stderr)
    print(f"unreferenced under scan roots: {len(rels)}", file=sys.stderr)
    for r in rels:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
