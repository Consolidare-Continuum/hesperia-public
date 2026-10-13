#!/usr/bin/env python3
# HESPERIA — Task 6 Phase 3.1: classify markdown-ish files for doc authority (heuristic).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: python3 tools/doc_authority_scan.py
# Output: tmp/doc_authority_scan.yaml

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_TMP = _REPO / "tmp"


def classify(rel: str) -> str:
    s = rel.replace("\\", "/").lower()
    if s.startswith("assets/specs/") or s.startswith("spec/"):
        if "release" in s or "historical" in s:
            return "descriptive_doc"
        return "canonical_spec"
    if "docs/research" in s or "research/" in s:
        return "research_note"
    if s.startswith("docs/governance") or s.startswith("docs/audit"):
        return "descriptive_doc"
    if s.startswith("docs/"):
        return "descriptive_doc"
    if s.startswith("legacy/"):
        return "obsolete"
    if s.endswith("readme.md"):
        return "descriptive_doc"
    return "descriptive_doc"


def main() -> int:
    _TMP.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for p in sorted(_REPO.rglob("*.md")):
        sp = str(p)
        if ".venv" in sp or "node_modules" in sp or "legacy/" in sp:
            continue
        try:
            rel = p.relative_to(_REPO).as_posix()
        except ValueError:
            continue
        rows.append({"path": rel, "class": classify(rel)})
    try:
        import yaml  # type: ignore
    except ImportError:
        import json

        out = _TMP / "doc_authority_scan.json"
        out.write_text(
            json.dumps(
                {"generated_utc": datetime.now(timezone.utc).isoformat(), "entries": rows},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {out} (install PyYAML for .yaml output)")
        return 0

    body = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "entries": rows,
    }
    out = _TMP / "doc_authority_scan.yaml"
    out.write_text(
        f"# doc_authority_scan — heuristic; refine manually.\n{yaml.safe_dump(body, sort_keys=False, allow_unicode=True)}",
        encoding="utf-8",
    )
    print(f"wrote {out} ({len(rows)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
