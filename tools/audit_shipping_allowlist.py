#!/usr/bin/env python3
# HESPERIA — Ensure shipping import allowlist stays minimal and used.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage:
#   python3 tools/audit_shipping_allowlist.py [--strict-unused] [--max-total-prefixes N]

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[1]
_ALLOWLIST = Path("runtime/shipping/shipping_import_allowlist.yaml")
_SHIPPING = Path("runtime/shipping")


def _collect_modules_from_shipping(repo: Path) -> set[str]:
    mods: set[str] = set()
    d = repo / _SHIPPING
    for py in sorted(d.rglob("*.py")):
        if "__pycache__" in str(py) or py.name == "shipping_import_allowlist.yaml":
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name:
                        mods.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module)
    return mods


def _prefix_used(prefix: str, used_modules: set[str]) -> bool:
    if prefix in used_modules:
        return True
    return any(m == prefix or m.startswith(prefix + ".") for m in used_modules)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit runtime/shipping import allowlist.")
    ap.add_argument("--repo", type=Path, default=_REPO)
    ap.add_argument(
        "--strict-unused",
        action="store_true",
        help="Exit 1 if an allowlist prefix is never imported (keeps list honest)",
    )
    ap.add_argument(
        "--max-total-prefixes",
        type=int,
        default=None,
        help="Optional cap on len(repo)+len(third) allowlist entries (creep detector)",
    )
    args = ap.parse_args()
    repo = args.repo.resolve()
    doc = yaml.safe_load((repo / _ALLOWLIST).read_text(encoding="utf-8")) or {}
    repo_p = [str(x) for x in (doc.get("allowed_repo_prefixes") or [])]
    third_p = [str(x) for x in (doc.get("allowed_third_party_prefixes") or [])]

    if args.max_total_prefixes is not None:
        tot = len(repo_p) + len(third_p)
        if tot > args.max_total_prefixes:
            print(
                f"audit_shipping_allowlist: FAIL allowlist size {tot} > --max-total-prefixes {args.max_total_prefixes}",
                file=sys.stderr,
            )
            return 1

    used_mods = _collect_modules_from_shipping(repo)

    exit_code = 0
    for label, prefixes in (("repo", repo_p), ("third_party", third_p)):
        for p in prefixes:
            if not _prefix_used(p, used_mods):
                msg = f"audit_shipping_allowlist: UNUSED {label} prefix {p!r} (no import under runtime/shipping)"
                print(msg, file=sys.stderr)
                if args.strict_unused:
                    exit_code = 1

    print(
        f"audit_shipping_allowlist: OK imports_collected={len(used_mods)} "
        f"repo_prefixes={len(repo_p)} third_party_prefixes={len(third_p)}",
        file=sys.stderr,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
