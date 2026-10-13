#!/usr/bin/env python3
# HESPERIA — Task 6 Phase 3.7: specs index → tmp/specs_index_preview.json
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage: python3 tools/build_specs_index.py [--out PATH]

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_DEFAULT_OUT = _REPO / "tmp" / "specs_index_preview.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build_index() -> dict:
    entries: list[dict[str, str]] = []
    for base in (_REPO / "assets" / "specs", _REPO / "spec"):
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.md")):
            rel = p.relative_to(_REPO).as_posix()
            entries.append({"path": rel, "sha256": _sha256_file(p)})
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "spec_files": entries,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    data = build_index()
    args.out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out} ({len(data['spec_files'])} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
