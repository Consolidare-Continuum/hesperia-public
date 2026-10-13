#!/usr/bin/env python3
"""
One-off script: prepend RAD legal header to all .py, .sh, .md files.
Run from repo root: python3 tools/scripts/add_legal_header.py
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

HEADER_PY_SH = """# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""

HEADER_MD = """<!--
HESPERIA — Reference Architecture Definition (RAD)
Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
Restricted Research Disclosure License. Inspection and reference only.
No reproduction, redistribution, or use without explicit written permission.
See LEGAL_NOTICE.md for full terms.
-->

"""

SKIP_PREFIXES = ("LEGAL_NOTICE.md",)
SKIP_DIRS = (".git", "__pycache__", "node_modules", ".pytest_cache")


def already_has_header(content: str, marker: str) -> bool:
    return "HESPERIA — Reference Architecture Definition (RAD)" in content[:1200] or marker in content[:800]


def process_py(path: Path) -> bool:
    raw = path.read_bytes()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if already_has_header(content, "LEGAL_NOTICE.md"):
        return False
    lines = content.splitlines(keepends=True)
    insert_at = 0
    while insert_at < len(lines) and insert_at < 3:
        line = lines[insert_at]
        if line.startswith("#!") or (line.strip().startswith("#") and ("coding" in line or "utf" in line.lower())):
            insert_at += 1
        else:
            break
    new_content = "".join(lines[:insert_at]) + ("\n" if insert_at > 0 and not lines[insert_at - 1].endswith("\n\n") else "") + HEADER_PY_SH + "".join(lines[insert_at:])
    path.write_bytes(new_content.encode("utf-8"))
    return True


def process_sh(path: Path) -> bool:
    raw = path.read_bytes()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if already_has_header(content, "LEGAL_NOTICE.md"):
        return False
    lines = content.splitlines(keepends=True)
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    new_content = "".join(lines[:insert_at]) + ("" if insert_at == 0 else "\n") + HEADER_PY_SH + "".join(lines[insert_at:])
    path.write_bytes(new_content.encode("utf-8"))
    return True


def process_md(path: Path) -> bool:
    if path.name == "LEGAL_NOTICE.md":
        return False
    raw = path.read_bytes()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if already_has_header(content, "LEGAL_NOTICE.md"):
        return False
    new_content = HEADER_MD + content
    path.write_bytes(new_content.encode("utf-8"))
    return True


def main():
    count = 0
    for root, dirs, filenames in os.walk(REPO_ROOT):
        root_path = Path(root)
        if any(s in Path(root).parts for s in SKIP_DIRS):
            continue
        for name in filenames:
            path = root_path / name
            if path.suffix == ".py":
                if process_py(path):
                    count += 1
                    print(path.relative_to(REPO_ROOT))
            elif path.suffix == ".sh":
                if process_sh(path):
                    count += 1
                    print(path.relative_to(REPO_ROOT))
            elif path.suffix == ".md":
                if process_md(path):
                    count += 1
                    print(path.relative_to(REPO_ROOT))
    print(f"Added header to {count} files.")


if __name__ == "__main__":
    main()
