#!/usr/bin/env python3
# HESPERIA — Emit markdown import graph for public runtime trees (CI diff target).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Regenerate committed docs:
#   python3 tools/gen_import_graph_doc.py --write
#   python3 tools/gen_import_graph_doc.py --write --profile engine
# CI check:
#   python3 tools/gen_import_graph_doc.py | diff -q docs/IMPORT_GRAPH_v0_5_0.md -
#   python3 tools/gen_import_graph_doc.py --profile engine | diff -q docs/IMPORT_GRAPH_ENGINE_v0_5_0.md -

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path

# Keep in sync with tools/check_import_boundary.py (forbidden policy narrative).
FORBIDDEN_PREFIXES = (
    "core.math.",
    "core.domain.bridge",
    "core.topology.invariant_catalog",
    "sphere.pipeline.pipeline_runner",
    "sphere.pipeline.layer_registry",
    "sphere.pipeline.pipeline_state",
)
FORBIDDEN_MODULE_ALIASES = (
    "core.attribution.structural",
    "core.contracts.layer_contract",
    "core.layers",
    "core.policy",
    "core.stability",
)

# Public runtime + product façade (services host run_structural_analysis).
SCAN_DIRS = [
    "runtime/api",
    "runtime/pipeline",
    "runtime/public_reports",
    "runtime/artifact_writer",
    "runtime/runners",
    "runtime/shipping",
    "runtime/services",
]

EXCLUDED_FILES = frozenset(
    {
        "runtime/pipeline/analyze.py",
        "runtime/pipeline/r1_r4_pipeline.py",
        "runtime/pipeline/batch_runner.py",
        "runtime/pipeline/reading_scales.py",
        "runtime/pipeline/run_corpus_benchmark.py",
    }
)

PROFILE_CONFIG: dict[str, dict[str, object]] = {
    "public": {
        "scan_dirs": SCAN_DIRS,
        "excluded": EXCLUDED_FILES,
        "out_name": "IMPORT_GRAPH_v0_5_0.md",
        "title": "Import graph — public runtime & services (v0.5.0 seal baseline)",
        "forbidden_section": True,
        "ci_hint": "python3 tools/gen_import_graph_doc.py | diff -q docs/IMPORT_GRAPH_v0_5_0.md -",
    },
    "engine": {
        "scan_dirs": ["hesperia/engine"],
        "excluded": frozenset(),
        "out_name": "IMPORT_GRAPH_ENGINE_v0_5_0.md",
        "title": "Import graph — `hesperia/engine` (v0.5.0 seal baseline)",
        "forbidden_section": False,
        "ci_hint": "python3 tools/gen_import_graph_doc.py --profile engine | diff -q docs/IMPORT_GRAPH_ENGINE_v0_5_0.md -",
    },
}


def _imports_from_source(text: str) -> tuple[list[str], list[str]]:
    """Return (bare_import_modules, from_modules)."""
    bare: list[str] = []
    from_mods: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return bare, from_mods
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    bare.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            from_mods.append(node.module)
    return sorted(set(bare)), sorted(set(from_mods))


def _collect(
    repo: Path,
    scan_dirs: list[str],
    excluded: frozenset[str],
) -> tuple[dict[str, tuple[list[str], list[str]]], dict[str, int]]:
    per_file: dict[str, tuple[list[str], list[str]]] = {}
    counts: dict[str, int] = defaultdict(int)
    for dir_name in scan_dirs:
        d = repo / dir_name
        if not d.is_dir():
            continue
        for py in sorted(d.rglob("*.py")):
            if "__pycache__" in str(py):
                continue
            try:
                rel = py.relative_to(repo).as_posix()
            except ValueError:
                continue
            if rel in excluded:
                continue
            text = py.read_text(encoding="utf-8")
            bare, froms = _imports_from_source(text)
            per_file[rel] = (bare, froms)
            for m in bare + froms:
                counts[m] += 1
    return per_file, dict(sorted(counts.items()))


def _emit_markdown(repo: Path, profile: str) -> str:
    cfg = PROFILE_CONFIG[profile]
    scan_dirs = list(cfg["scan_dirs"])  # type: ignore[arg-type]
    excluded = cfg["excluded"]  # type: ignore[assignment]
    title = str(cfg["title"])
    show_forbidden = bool(cfg["forbidden_section"])
    ci_hint = str(cfg["ci_hint"])
    write_cmd = (
        "python3 tools/gen_import_graph_doc.py --write"
        if profile == "public"
        else "python3 tools/gen_import_graph_doc.py --write --profile engine"
    )
    per_file, counts = _collect(repo, scan_dirs, excluded)
    lines: list[str] = [
        "<!--",
        "  HESPERIA — Generated file. Regenerate:",
        f"    {write_cmd}",
        "  CI drift check:",
        f"    {ci_hint}",
        "-->",
        "",
        f"# {title}",
        "",
        "This document lists **static** `import` / `from` targets seen under the scanned trees. "
        "It is a **drift detector**: unexpected new edges often mean a boundary or layering mistake.",
        "",
        "## Scanned directories",
        "",
    ]
    for d in scan_dirs:
        lines.append(f"- `{d}/`")
    if excluded:
        lines.extend(
            [
                "",
                "## Excluded files (see `tools/check_import_boundary.py`)",
                "",
            ]
        )
        for f in sorted(excluded):
            lines.append(f"- `{f}`")
    if show_forbidden:
        lines.extend(
            [
                "",
                "## Forbidden targets (must never appear in scanned public-runtime files)",
                "",
                "Enforced by `python3 tools/check_import_boundary.py`.",
                "",
                "### Prefixes",
                "",
            ]
        )
        for p in FORBIDDEN_PREFIXES:
            lines.append(f"- `{p}*`")
        lines.extend(["", "### Module aliases", ""])
        for m in FORBIDDEN_MODULE_ALIASES:
            lines.append(f"- `{m}`")
    lines.extend(["", "## Aggregate import targets (reference count)", ""])
    for mod, n in counts.items():
        lines.append(f"- `{mod}` — **{n}**")
    lines.extend(["", "## Per-file edges (sorted by path)", ""])
    for path in sorted(per_file.keys()):
        bare, froms = per_file[path]
        lines.append(f"### `{path}`")
        lines.append("")
        if bare:
            lines.append("**import**")
            for m in bare:
                lines.append(f"- `{m}`")
            lines.append("")
        if froms:
            lines.append("**from**")
            for m in froms:
                lines.append(f"- `{m}`")
            lines.append("")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate IMPORT_GRAPH markdown for CI diff.")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--profile", choices=sorted(PROFILE_CONFIG.keys()), default="public")
    ap.add_argument(
        "--write",
        action="store_true",
        help="Write docs/<IMPORT_GRAPH*.md> for selected profile",
    )
    args = ap.parse_args()
    body = _emit_markdown(args.repo, args.profile)
    if args.write:
        out_name = str(PROFILE_CONFIG[args.profile]["out_name"])
        out = args.repo / "docs" / out_name
        out.write_text(body, encoding="utf-8")
        print(f"wrote {out}", file=sys.stderr)
        return 0
    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
