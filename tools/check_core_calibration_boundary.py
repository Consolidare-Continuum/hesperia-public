#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Fail when the Class A default package references the opt-in TFP package."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def _constant_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _constant_string(node.left)
        right = _constant_string(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def _references_tfp_package(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.casefold().startswith("hesperia.modules.tfp") for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").casefold()
            if module.startswith("hesperia.modules.tfp"):
                return True
            if (
                module == "hesperia.modules" or node.level > 0
            ) and any(alias.name.casefold() == "tfp" for alias in node.names):
                return True
        elif isinstance(node, ast.Call) and node.args:
            function_name = ""
            if isinstance(node.func, ast.Name):
                function_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                function_name = node.func.attr
            imported = _constant_string(node.args[0])
            if (
                function_name in {"__import__", "import_module"}
                and imported is not None
                and imported.casefold().startswith("hesperia.modules.tfp")
            ):
                return True
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = _constant_string(node.value)
            if value is not None and (
                value.casefold() == "tfp"
                or "hesperia.modules.tfp" in value.casefold()
            ):
                return True
    return False


def check_boundary(repo_root: Path) -> list[str]:
    default_root = repo_root / "hesperia/modules/default"
    if not default_root.is_dir():
        return ["missing hesperia/modules/default"]

    errors: list[str] = []
    for path in sorted(default_root.rglob("*")):
        relative = path.relative_to(repo_root)
        if path.is_symlink():
            errors.append(f"{relative}: symlink is forbidden in default module")
            continue
        if any(part.casefold() == "tfp" or "tfp" in part.casefold() for part in relative.parts):
            errors.append(f"{relative}: TFP path is forbidden in default module")
            continue
        if path.is_file() and path.suffix == ".py":
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"{relative}: unreadable source: {exc}")
                continue
            if _references_tfp_package(source):
                errors.append(f"{relative}: TFP package reference is forbidden")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors = check_boundary(args.repo_root.resolve())
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: core calibration default-module boundary is clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
