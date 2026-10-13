# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Enforce: sphere/* must not implement math; they must call core.math.

Reject patterns in sphere:
- numpy math operations (np.sum, np.dot, np.argmax, np.max for formulas)
- manual entropy (math.log, math.log2)
- manual matrix multiplication

Allow: np.asarray for type coercion; imports from core.math.
"""

from __future__ import annotations

import re
from pathlib import Path


# Forbidden patterns: (pattern, description)
_FORBIDDEN = [
    (re.compile(r"\bnp\.sum\s*\("), "np.sum (use core.math)"),
    (re.compile(r"\bnp\.dot\s*\("), "np.dot (use core.math)"),
    (re.compile(r"\bnp\.(matmul|@)\s*"), "matrix multiply (use core.math)"),
    (re.compile(r"\bnp\.argmax\s*\("), "np.argmax (use core.math)"),
    (re.compile(r"\bmath\.log2?\s*\("), "math.log/log2 (use core.math entropy)"),
]


def _sphere_py_files() -> list[Path]:
    root = Path(__file__).resolve().parents[2]
    sphere = root / "sphere"
    if not sphere.exists():
        return []
    return list(sphere.rglob("*.py"))


def _file_imports_core_math(content: str) -> bool:
    return "from core.math" in content or "import core.math" in content


def _line_is_import(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("from ") or stripped.startswith("import ")


def _has_forbidden_math(content: str, path: Path) -> list[tuple[int, str, str]]:
    violations = []
    for i, line in enumerate(content.splitlines(), 1):
        if _line_is_import(line) and "core.math" in line:
            continue
        for pattern, desc in _FORBIDDEN:
            if pattern.search(line):
                violations.append((i, desc, line.strip()[:80]))
                break
    return violations


def test_no_math_in_sphere():
    """Sphere modules must not contain numerical formula implementations; they must use core.math."""
    root = Path(__file__).resolve().parents[2]
    sphere = root / "sphere"
    if not sphere.exists():
        return
    all_violations = []
    for py_path in _sphere_py_files():
        content = py_path.read_text(encoding="utf-8")
        rel = py_path.relative_to(root)
        violations = _has_forbidden_math(content, py_path)
        for line_no, desc, snippet in violations:
            all_violations.append(f"{rel}:{line_no}: {desc} -> {snippet!r}")
    assert not all_violations, (
        "Sphere must not implement math; use core.math instead.\n"
        + "\n".join(all_violations)
    )


def test_sphere_metrics_import_from_core_math():
    """Sphere metrics/dynamism modules that re-export math must import from core.math."""
    root = Path(__file__).resolve().parents[2]
    for sub in ("sphere/metrics", "sphere/dynamism"):
        dir_path = root / sub
        if not dir_path.exists():
            continue
        for py in dir_path.glob("*.py"):
            if py.name == "__init__.py":
                continue
            content = py.read_text(encoding="utf-8")
            if "compute_entropy" in content or "compute_curvature" in content or "compute_stability" in content:
                assert "from core.math" in content or "import core.math" in content, (
                    f"{py.relative_to(root)} should import from core.math"
                )
