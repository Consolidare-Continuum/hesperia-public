# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
RAD guard: enforce architecture boundaries.
- core does not import sphere
- core does not import runtime
- sphere does not import runtime

Allowed: runtime → sphere → core.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _py_files_under(root: Path, dirname: str) -> list[Path]:
    folder = root / dirname
    if not folder.is_dir():
        return []
    return [p for p in folder.rglob("*.py") if p.is_file()]


def _imports_module(content: str, module: str) -> list[tuple[int, str]]:
    """Return (line_no, line) for lines that import the given top-level module."""
    out = []
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # from sphere... / import sphere / from runtime... / import runtime
        if re.match(rf"from\s+{re.escape(module)}\b", stripped) or re.match(
            rf"import\s+{re.escape(module)}\b", stripped
        ):
            out.append((i, line))
    return out


def test_core_does_not_import_sphere():
    """Core must not depend on sphere."""
    root = _repo_root()
    violations = []
    for py_path in _py_files_under(root, "core"):
        content = py_path.read_text(encoding="utf-8")
        rel = py_path.relative_to(root)
        for line_no, line in _imports_module(content, "sphere"):
            violations.append(f"{rel}:{line_no}: {line.strip()!r}")
    assert not violations, "core must not import sphere.\n" + "\n".join(violations)


def test_core_does_not_import_runtime():
    """Core must not depend on runtime."""
    root = _repo_root()
    violations = []
    for py_path in _py_files_under(root, "core"):
        content = py_path.read_text(encoding="utf-8")
        rel = py_path.relative_to(root)
        for line_no, line in _imports_module(content, "runtime"):
            violations.append(f"{rel}:{line_no}: {line.strip()!r}")
    assert not violations, "core must not import runtime.\n" + "\n".join(violations)


def test_sphere_does_not_import_runtime():
    """Sphere must not depend on runtime."""
    root = _repo_root()
    violations = []
    for py_path in _py_files_under(root, "sphere"):
        content = py_path.read_text(encoding="utf-8")
        rel = py_path.relative_to(root)
        for line_no, line in _imports_module(content, "runtime"):
            violations.append(f"{rel}:{line_no}: {line.strip()!r}")
    assert not violations, "sphere must not import runtime.\n" + "\n".join(violations)
