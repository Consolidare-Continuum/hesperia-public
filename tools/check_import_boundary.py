#!/usr/bin/env python3
# HESPERIA — Import boundary check. Fail if public runtime imports internal compute modules.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""
Scan public runtime paths for forbidden imports. Exit 1 if any found.
Usage: python3 tools/check_import_boundary.py [--repo PATH]
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# Forbidden: public runtime must not import these
FORBIDDEN_PREFIXES = (
    "core.math.",
    "core.domain.bridge",
    "core.topology.invariant_catalog",
    "sphere.pipeline.pipeline_runner",
    "sphere.pipeline.layer_registry",
    "sphere.pipeline.pipeline_state",
)
FORBIDDEN_MODULE_ALIASES = (
    "core.attribution.structural",  # attribute, load_dict_a, tokenize, etc. — only in services
    "core.contracts.layer_contract",
    "core.layers",  # compute_L*, build_canonical_stub_adjacency, load_structure_profile, load_defaults from pipeline
    "core.policy",
    "core.stability",
)

# Paths considered "public runtime" (subject to check). Pipeline must only use core.services / core.projection / runtime.artifact_writer.
PUBLIC_RUNTIME_DIRS = ["runtime/api", "runtime/pipeline", "runtime/public_reports", "runtime/artifact_writer", "runtime/runners", "runtime/shipping"]
# Files excluded: internal-review or not yet migrated to service-only (see ENTRYPOINT_CLASSIFICATION).
EXCLUDED_FILES = [
    "runtime/pipeline/analyze.py",
    "runtime/pipeline/r1_r4_pipeline.py",
    "runtime/pipeline/batch_runner.py",
    "runtime/pipeline/reading_scales.py",
    "runtime/pipeline/run_corpus_benchmark.py",
]


def _check_node(node: ast.AST, file_path: Path, repo_root: Path) -> list[tuple[int, str]]:
    violations = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            mod = alias.name
            for prefix in FORBIDDEN_PREFIXES:
                if mod.startswith(prefix) or mod == prefix.rstrip("."):
                    violations.append((node.lineno, f"forbidden import: {mod}"))
            for fb in FORBIDDEN_MODULE_ALIASES:
                if mod == fb or (mod and mod.startswith(fb + ".")):
                    violations.append((node.lineno, f"forbidden import: {mod}"))
    if isinstance(node, ast.ImportFrom):
        if node.module is None:
            return violations
        mod = node.module
        for prefix in FORBIDDEN_PREFIXES:
            if mod and (mod.startswith(prefix) or mod == prefix.rstrip(".")):
                violations.append((node.lineno, f"forbidden from: {mod}"))
        for fb in FORBIDDEN_MODULE_ALIASES:
            if mod and (mod == fb or mod.startswith(fb + ".")):
                violations.append((node.lineno, f"forbidden from: {mod}"))
    return violations


def scan_file(path: Path, repo_root: Path) -> list[tuple[Path, int, str]]:
    out = []
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            for line_no, msg in _check_node(node, path, repo_root):
                out.append((path, line_no, msg))
    except (SyntaxError, OSError):
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Check public runtime for forbidden imports.")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    repo = args.repo
    all_violations = []
    for dir_name in PUBLIC_RUNTIME_DIRS:
        d = repo / dir_name
        if not d.exists():
            continue
        for py in d.rglob("*.py"):
            if "__pycache__" in str(py):
                continue
            try:
                rel = py.relative_to(repo)
                if str(rel).replace("\\", "/") in EXCLUDED_FILES:
                    continue
            except ValueError:
                pass
            all_violations.extend(scan_file(py, repo))
    if all_violations:
        for path, line_no, msg in all_violations[:80]:
            rel = path.relative_to(repo) if repo in path.parents else path
            print(f"{rel}:{line_no}: {msg}")
        if len(all_violations) > 80:
            print(f"... and {len(all_violations) - 80} more")
        print(f"Total: {len(all_violations)} import boundary violation(s).", file=sys.stderr)
        return 1
    print("Import boundary check: no violations.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
