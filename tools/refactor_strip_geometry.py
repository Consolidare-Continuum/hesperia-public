#!/usr/bin/env python3
# HESPERIA — Optional geometry→operational text refactor (audit / phased apply).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# WARNING: This repository uses "hex", "sphere", etc. as CANONICAL engine identifiers.
# Do not use --whole-repo-apply without architecture sign-off — see
# docs/governance/working/ETHAN-GEOMETRY-DECONTAMINATION-TASK.md §0.

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Dir name matches anywhere in path.parts → skip
_EXCLUDE_DIR_NAMES = frozenset(
    {
        "assets",
        "calibration_runs",
        "build",
        ".git",
        "venv",
        ".venv",
        "__pycache__",
        "node_modules",
        "legacy",
        "release",
        "outputs",
        "tmp",
        "dist",
        ".eggs",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
)

# Order matters: longer / more specific patterns first where overlaps exist
_RENAME_PATTERNS: list[tuple[str, str]] = [
    (r"\bhexagons\b", "units"),
    (r"\bhexagon\b", "unit"),
    (r"\bhexes\b", "units"),
    (r"\bhex\b", "unit"),
    (r"\bspherical\b", "domain-based"),
    (r"\bsphere\b", "domain"),
    (r"\bcoordinates\b", "indices"),
    (r"\bcoordinate\b", "index"),
    (r"\bneighbors\b", "related_units"),
    (r"\bneighbour\b", "related_units"),
    (r"\bgeometry\b", "structure"),
    (r"\bgeometric\b", "structural"),
    (r"\bmesh\b", "topology"),
    (r"\blattice\b", "topology"),
    (r"\bdistance\b", "interaction_score"),
    (r"\bgrid\b", "layout"),
    (r"\bloop\b", "cycle"),
]

_TEXT_EXT = frozenset({".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".rst"})

_CONFIRM_ENV = "HESPERIA_GEOMETRY_REFACTOR_WHOLE_REPO_CONFIRM"
_DEFAULT_REPORT = _REPO_ROOT / "outputs" / "geometry_refactor_report.json"
_DEFAULT_VALIDATE_REPORT = _REPO_ROOT / "outputs" / "geometry_validation_report.json"


def _should_skip(path: Path, *, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return True
    return any(part in _EXCLUDE_DIR_NAMES for part in path.parts)


def _under_allowed_apply_roots(rel: Path, roots: list[str]) -> bool:
    s = rel.as_posix()
    return any(s == r or s.startswith(r + "/") for r in roots)


def _process_file(
    path: Path,
    *,
    apply: bool,
    patterns: list[tuple[str, str]],
) -> tuple[str | None, list[dict[str, object]]]:
    try:
        original = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return None, [{"error": str(e)}]

    updated = original
    changes: list[dict[str, object]] = []

    for pattern, repl in patterns:
        matches = list(re.finditer(pattern, updated))
        if not matches:
            continue
        updated = re.sub(pattern, repl, updated)
        changes.append({"pattern": pattern, "replacement": repl, "count": len(matches)})

    if changes and apply and updated != original:
        path.write_text(updated, encoding="utf-8")

    return updated, changes


def _iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in _TEXT_EXT:
            continue
        if _should_skip(p, root=root):
            continue
        out.append(p)
    return sorted(out)


def run_refactor(
    *,
    root: Path,
    apply: bool,
    whole_repo_apply: bool,
    apply_roots: list[str],
    report_path: Path,
    log: bool = True,
) -> list[dict[str, object]]:
    report: list[dict[str, object]] = []
    files = _iter_files(root)

    for path in files:
        rel = path.relative_to(root)
        if apply and not whole_repo_apply:
            if not _under_allowed_apply_roots(rel, apply_roots):
                continue

        updated, changes = _process_file(path, apply=apply, patterns=_RENAME_PATTERNS)
        if updated is None:
            report.append({"file": str(rel), "changes": [], "error": changes[0].get("error")})
            continue
        if changes:
            report.append({"file": str(rel), "changes": changes})

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if log:
        print(f"Wrote {report_path} ({len(report)} files with matches).", file=sys.stderr)
    return report


def run_validate(*, root: Path, report_path: Path, log: bool = True) -> dict[str, object]:
    """Scan for remaining forbidden tokens (word-bound); no writes except report."""
    files = _iter_files(root)
    findings: list[dict[str, object]] = []
    pattern_src = [p for p, _ in _RENAME_PATTERNS if p != r"\binteraction_score\b"]

    for path in files:
        rel = str(path.relative_to(root))
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            findings.append({"file": rel, "error": str(e)})
            continue
        per_file: list[dict[str, object]] = []
        for pat in pattern_src:
            n = len(re.findall(pat, text))
            if n:
                per_file.append({"pattern": pat, "count": n})
        if per_file:
            findings.append({"file": rel, "matches": per_file})

    out: dict[str, object] = {
        "root": str(root),
        "files_scanned": len(files),
        "files_with_forbidden": len(findings),
        "findings": findings,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    if log:
        print(
            f"Wrote {report_path} — files_with_forbidden={len(findings)}.",
            file=sys.stderr,
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Geometry→operational wording refactor (dry-run by default). "
        "See docs/governance/working/ETHAN-GEOMETRY-DECONTAMINATION-TASK.md",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_REPO_ROOT,
        help="Repository root (default: Hesperia repo root)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes (default: dry-run only). Scoped to --apply-roots unless --whole-repo-apply.",
    )
    parser.add_argument(
        "--apply-roots",
        default="docs,specs",
        help="Comma-separated relative roots for --apply (default: docs,specs)",
    )
    parser.add_argument(
        "--whole-repo-apply",
        action="store_true",
        help=f"DANGEROUS: apply to all scanned text files. Requires env {_CONFIRM_ENV}=1.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=_DEFAULT_REPORT,
        help="JSON report path for refactor dry-run/apply",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only scan for remaining forbidden tokens; write geometry_validation_report.json",
    )
    parser.add_argument(
        "--validate-report",
        type=Path,
        default=_DEFAULT_VALIDATE_REPORT,
        help="Output path for --validate",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    if args.validate:
        run_validate(root=root, report_path=args.validate_report.resolve())
        return 0

    apply_roots = [x.strip() for x in str(args.apply_roots).split(",") if x.strip()]

    if args.apply:
        if args.whole_repo_apply:
            if os.environ.get(_CONFIRM_ENV) != "1":
                print(
                    f"Refuse whole-repo --apply: set {_CONFIRM_ENV}=1 after reading "
                    "docs/governance/working/ETHAN-GEOMETRY-DECONTAMINATION-TASK.md §0.",
                    file=sys.stderr,
                )
                return 2
        else:
            print(
                f"Apply mode: limiting writes to roots {apply_roots!r} "
                "(use --whole-repo-apply for full tree; dangerous).",
                file=sys.stderr,
            )

    run_refactor(
        root=root,
        apply=bool(args.apply),
        whole_repo_apply=bool(args.whole_repo_apply),
        apply_roots=apply_roots,
        report_path=args.report.resolve(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
