#!/usr/bin/env python3
# HESPERIA — Task 6 Phase 0: repo inventory + version scan + module draft + preseal snapshot.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage (repo root):  python3 tools/seal_phase0_inventory.py
# Writes under tmp/ (gitignored except .gitkeep).

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_TMP = _REPO / "tmp"
_VERSION_PATTERNS = (
    r"v0\.4",
    r"v0\.5",
    r"v050",
    r"v060",
    r"current baseline",
    r"architecture baseline",
    r"schema_version",
    r"VERSION",
)


def _ensure_tmp() -> None:
    _TMP.mkdir(parents=True, exist_ok=True)


def _write_repo_inventory() -> Path:
    lines: list[str] = []
    lines.append(f"# repo_inventory generated {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append("## top_level_directories")
    for p in sorted(_REPO.iterdir()):
        if p.is_dir() and not p.name.startswith("."):
            lines.append(p.name)
    lines.append("\n## py_files (relative)")
    for p in sorted(_REPO.rglob("*.py")):
        if "legacy/" in str(p) or ".venv" in str(p) or "__pycache__" in str(p):
            continue
        try:
            lines.append(p.relative_to(_REPO).as_posix())
        except ValueError:
            pass
    lines.append("\n## md_files (relative)")
    for p in sorted(_REPO.rglob("*.md")):
        if "legacy/" in str(p) or ".venv" in str(p):
            continue
        try:
            lines.append(p.relative_to(_REPO).as_posix())
        except ValueError:
            pass
    lines.append("\n## json_yaml_config (relative)")
    for pat in ("*.json", "*.yaml", "*.yml"):
        for p in sorted(_REPO.rglob(pat)):
            sp = str(p)
            if "legacy/" in sp or ".venv" in sp or "node_modules" in sp or "__pycache__" in sp:
                continue
            if p.name in ("package-lock.json",):
                continue
            try:
                lines.append(p.relative_to(_REPO).as_posix())
            except ValueError:
                pass
    lines.append("\n## output_artifact_roots")
    for name in (
        "outputs",
        "assets/artifacts",
        "release",
        "dist",
        "build",
    ):
        d = _REPO / name
        if d.is_dir():
            lines.append(name + "/")
    out = _TMP / "repo_inventory.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _write_version_scan() -> Path:
    lines: list[str] = []
    lines.append(f"# version_reference_scan {datetime.now(timezone.utc).isoformat()} UTC")
    combined = "|".join(f"({p})" for p in _VERSION_PATTERNS)
    rx = re.compile(combined, re.I)
    seen: set[str] = set()
    for p in sorted(_REPO.rglob("*")):
        if not p.is_file() or p.suffix not in (".md", ".py", ".yaml", ".yml", ".json", ".toml"):
            continue
        sp = str(p)
        if "legacy/" in sp or ".venv" in sp or "__pycache__" in sp or "node_modules" in sp:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in rx.finditer(text):
            rel = p.relative_to(_REPO).as_posix()
            key = f"{rel}:{m.start()}:{m.group(0)!r}"
            if key not in seen:
                seen.add(key)
                line_no = text[: m.start()].count("\n") + 1
                lines.append(f"{rel}:{line_no}: {m.group(0)}")
    out = _TMP / "version_reference_scan.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _write_module_classification_draft() -> Path:
    """High-level folder classification (manual refinement expected)."""
    mapping: dict[str, str] = {}
    for name, bucket in (
        ("core", "core"),
        ("hesperia", "engine"),
        ("runtime", "system"),
        ("lexicon", "system"),
        ("schemas", "schema"),
        ("specs", "specs"),
        ("spec", "specs"),
        ("docs", "docs"),
        ("tests", "tests"),
        ("tools", "tools"),
        ("examples", "examples"),
        ("research", "research"),
        ("assets", "outputs"),
        ("outputs", "outputs"),
        ("release", "outputs"),
        ("legacy", "archive"),
        ("dist", "outputs"),
        ("build", "outputs"),
    ):
        if (_REPO / name).exists():
            mapping[name] = bucket
    text = (
        f"# module_classification_draft — Task 6 Phase 0.3\n"
        f"# generated {datetime.now(timezone.utc).isoformat()} UTC\n"
        f"# Refine before using as policy.\n\n"
    )
    import yaml  # type: ignore

    text += yaml.safe_dump({"top_level": mapping}, sort_keys=True, allow_unicode=True)
    out = _TMP / "module_classification_draft.yaml"
    out.write_text(text, encoding="utf-8")
    return out


def _write_preseal_snapshot() -> Path:
    sys.path.insert(0, str(_REPO))
    from runtime.services.analysis_service import run_structural_analysis

    fixture = _REPO / "tests" / "fixtures" / "release_v0_5_0" / "canonical_input.txt"
    text = fixture.read_text(encoding="utf-8").strip() if fixture.is_file() else "smoke"
    assets = _REPO / "assets" / "lexicon" / "curated"
    result = run_structural_analysis(text, assets_root=assets, stages="full")
    snap = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "fixture": str(fixture.relative_to(_REPO)) if fixture.is_file() else None,
        "system_version": result.get("system_version"),
        "schema_version": result.get("schema_version"),
        "build_id": result.get("build_id"),
        "calibration_profile": result.get("calibration_profile"),
    }
    out = _TMP / "preseal_snapshot.json"
    out.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    _ensure_tmp()
    paths = [
        _write_repo_inventory(),
        _write_version_scan(),
        _write_module_classification_draft(),
        _write_preseal_snapshot(),
    ]
    print("Phase 0 inventory wrote:")
    for p in paths:
        print(" ", p.relative_to(_REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
