#!/usr/bin/env python3
# HESPERIA — Build a zip-safe, portable release bundle.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Core goal: eliminate path-length / encoding edge cases by copying the repo
# into a temp dir, excluding problematic paths, and writing a normalized zip.

from __future__ import annotations

import os
import re
import shutil
import zipfile


SRC = "."
TMP = "_release_tmp"

EXCLUDE_PREFIXES = [
    ".git",
    "__pycache__",
    "research/_noone_local",
    "assets/calibration/dicts",
    "hesperia/modules/tfp/data/corpus",
    "hesperia/modules/tfp/data/tfp_v1/corpus",
    "outputs",
    # Clinical session Markdown (same sensitivity as research/_noone_local)
    "hesperia/modules/tfp/data/tfp_v1/corpus/sessions",
]


def _norm_rel(p: str) -> str:
    # Normalize to forward slashes so zip entries are consistent across OSes.
    return p.replace("\\", "/").lstrip("./")


def should_exclude(rel_path: str) -> bool:
    rel_path_n = _norm_rel(rel_path)
    for e in EXCLUDE_PREFIXES:
        e_n = _norm_rel(e)
        if rel_path_n == e_n:
            return True
        if rel_path_n.startswith(e_n + "/"):
            return True
    return False


def _version_from_env_or_default() -> str:
    v = os.environ.get("HESPERIA_VERSION", "").strip()
    if v:
        return v
    try:
        text = open("VERSION.yaml", "r", encoding="utf-8").read()
    except OSError:
        return "unknown"
    match = re.search(r'^\s*system_version:\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else "unknown"


def main() -> int:
    version = _version_from_env_or_default()
    out_base = f"release_bundle_v{version}"

    zip_path = f"{out_base}.zip"
    if os.path.exists(TMP):
        shutil.rmtree(TMP)

    if os.path.exists(zip_path):
        os.remove(zip_path)

    src_root = os.path.abspath(SRC)
    tmp_root = os.path.abspath(TMP)

    # Copy repo into a temp dir so the produced zip does not depend on any
    # on-disk quirks (paths/encoding) from the original working tree.
    def _ignore(dir_path: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            full = os.path.join(dir_path, name)
            rel = os.path.relpath(full, src_root)
            if should_exclude(rel):
                ignored.add(name)
        return ignored

    shutil.copytree(SRC, TMP, ignore=_ignore)

    # Deterministic entry order: collect, sort by archive-relative name, then write.
    entries: list[tuple[str, str]] = []
    for root, _, files in os.walk(tmp_root):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, tmp_root)
            rel_n = _norm_rel(rel)
            # Skip excluded prefixes (keeps bundle contents aligned with copytree ignore).
            if should_exclude(rel_n):
                continue
            entries.append((rel_n, full))

    entries.sort(key=lambda x: x[0])

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for rel_n, full in entries:
            z.write(full, rel_n)

    shutil.rmtree(TMP)
    print(f"build_release_bundle: wrote {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
