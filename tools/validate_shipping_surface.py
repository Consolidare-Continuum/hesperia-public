#!/usr/bin/env python3
# HESPERIA — Enforce explicit allowlist for imports under runtime/shipping/*.py
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: python3 tools/validate_shipping_surface.py [--repo PATH]

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[1]
_ALLOWLIST_PATH = Path("runtime/shipping/shipping_import_allowlist.yaml")
_SHIPPING_DIR = Path("runtime/shipping")


def _load_allowlist(repo: Path) -> tuple[list[str], list[str]]:
    p = repo / _ALLOWLIST_PATH
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    repo_p = [str(x) for x in (doc.get("allowed_repo_prefixes") or [])]
    third = [str(x) for x in (doc.get("allowed_third_party_prefixes") or [])]
    return repo_p, third


def _stdlib_names() -> frozenset[str]:
    names = getattr(sys, "stdlib_module_names", None)
    if isinstance(names, frozenset):
        return names
    if isinstance(names, set):
        return frozenset(names)
    # Python < 3.10 fallback (minimal)
    return frozenset(
        {
            "abc",
            "argparse",
            "ast",
            "base64",
            "collections",
            "copy",
            "dataclasses",
            "datetime",
            "enum",
            "functools",
            "hashlib",
            "importlib",
            "io",
            "itertools",
            "json",
            "logging",
            "math",
            "os",
            "pathlib",
            "re",
            "subprocess",
            "sys",
            "time",
            "typing",
            "urllib",
            "uuid",
        }
    )


def _allowed_module(mod: str, repo_prefixes: list[str], third_prefixes: list[str]) -> bool:
    if not mod:
        return True
    if mod == "__future__":
        return True
    root = mod.split(".", 1)[0]
    if root in _stdlib_names():
        return True
    for p in repo_prefixes:
        if mod == p or mod.startswith(p + "."):
            return True
    for p in third_prefixes:
        if mod == p or mod.startswith(p + "."):
            return True
    return False


def _collect_imports(path: Path) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    out.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.append((node.lineno, node.module))
            # relative from .x — module None; skip (only runtime.shipping internal relative — should not exist)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate runtime/shipping imports against allowlist.")
    ap.add_argument("--repo", type=Path, default=_REPO)
    args = ap.parse_args()
    repo = args.repo.resolve()
    ship = repo / _SHIPPING_DIR
    if not ship.is_dir():
        print(f"missing {_SHIPPING_DIR}", file=sys.stderr)
        return 1
    repo_prefixes, third_prefixes = _load_allowlist(repo)
    bad: list[str] = []
    for py in sorted(ship.rglob("*.py")):
        if "__pycache__" in str(py):
            continue
        rel = py.relative_to(repo).as_posix()
        for lineno, mod in _collect_imports(py):
            if _allowed_module(mod, repo_prefixes, third_prefixes):
                continue
            bad.append(f"{rel}:{lineno}: disallowed import {mod!r}")
    if bad:
        for b in bad:
            print(b, file=sys.stderr)
        print(f"validate_shipping_surface: FAIL ({len(bad)} violation(s))", file=sys.stderr)
        return 1
    print("validate_shipping_surface: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
