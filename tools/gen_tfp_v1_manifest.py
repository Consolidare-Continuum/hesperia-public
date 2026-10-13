#!/usr/bin/env python3
# TFP-DATA-T08: Write hesperia/modules/tfp/data/tfp_v1/MANIFEST.yaml (checksums).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("gen_tfp_v1_manifest: need PyYAML", file=sys.stderr)
    raise SystemExit(1)


def _dir_sha256(root: Path) -> str:
    """Deterministic hash over relative paths + file sha256."""
    h = hashlib.sha256()
    if not root.is_dir():
        return ""
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            rel = p.relative_to(root).as_posix().encode()
            h.update(rel)
            h.update(b"\0")
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    repo = args.repo.resolve()
    tfp = repo / "hesperia" / "modules" / "tfp" / "data" / "tfp_v1"
    ru = tfp / "corpus" / "original" / "ru"
    en = tfp / "corpus" / "original" / "en"
    sess = tfp / "corpus" / "sessions"
    da = tfp / "dict_a" / "runtime" / "dict_a.jsonl"

    doc: dict = {
        "layout_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus": {
            "original_ru_sha256": _dir_sha256(ru),
            "original_en_sha256": _dir_sha256(en),
            "sessions_md_sha256": _dir_sha256(sess),
        },
        "dict_a_runtime": {},
    }
    if da.is_file():
        doc["dict_a_runtime"] = {
            "path": "dict_a/runtime/dict_a.jsonl",
            "sha256": hashlib.sha256(da.read_bytes()).hexdigest(),
        }
    tfp.mkdir(parents=True, exist_ok=True)
    out = tfp / "MANIFEST.yaml"
    out.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
