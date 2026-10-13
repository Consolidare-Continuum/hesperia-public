#!/usr/bin/env python3
# Regenerate docs/governance/working/TFP_DATA_T02_research_inventory.json (TFP-DATA-T02).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "governance" / "working" / "TFP_DATA_T02_research_inventory.json"
SKIP_DIR = {".git", "__pycache__", ".venv", "node_modules"}


def scan_tree(base: Path) -> dict:
    if not base.is_dir():
        return {"error": "missing", "path": str(base)}
    total_files = 0
    total_bytes = 0
    by_top: dict[str, dict] = {}
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
        rel = Path(dirpath).relative_to(base)
        top = rel.parts[0] if rel.parts else "."
        if top not in by_top:
            by_top[top] = {"files": 0, "bytes": 0, "purpose_tag": "scratch"}
        for f in filenames:
            fp = Path(dirpath) / f
            try:
                st = fp.stat()
            except OSError:
                continue
            if not fp.is_file():
                continue
            total_files += 1
            total_bytes += st.st_size
            by_top[top]["files"] += 1
            by_top[top]["bytes"] += st.st_size
    for name in by_top:
        ln = name.lower()
        if "clean" in ln or ln in ("2_cleaned", "english_2_cleaned"):
            by_top[name]["purpose_tag"] = "corpus"
        elif "dict" in ln or "calib" in ln:
            by_top[name]["purpose_tag"] = "dict_a_lineage"
    return {
        "root": str(base.relative_to(REPO)),
        "total_files": total_files,
        "total_bytes": total_bytes,
        "by_top_level": by_top,
    }


def find_research_refs() -> dict[str, list[str]]:
    patterns = [
        re.compile(r"research/_noone_local"),
        re.compile(r"research/[a-zA-Z0-9_./-]+"),
    ]
    hits: dict[str, set[str]] = {p.pattern: set() for p in patterns}
    roots = [REPO / "tools", REPO / "hesperia", REPO / "runtime", REPO / "tests", REPO / "docs", REPO / ".github"]
    exts = {".py", ".md", ".sh", ".yml", ".yaml"}
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
            for fn in filenames:
                if Path(fn).suffix.lower() not in exts:
                    continue
                fp = Path(dirpath) / fn
                try:
                    text = fp.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                rel = str(fp.relative_to(REPO))
                for p in patterns:
                    if p.search(text):
                        hits[p.pattern].add(rel)
    return {k: sorted(v) for k, v in hits.items()}


def main() -> int:
    noone = REPO / "research" / "_noone_local"
    doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO),
        "task": "TFP-DATA-T02",
        "research__noone_local_scan": scan_tree(noone),
        "reference_files_by_pattern": find_research_refs(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
