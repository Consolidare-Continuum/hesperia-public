#!/usr/bin/env python3
# TFP-DATA-T07: Copy outputs/dict_calibration/** → tfp_v1/provenance/api/runs/ with light secret redaction.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Usage (repo root): python3 tools/copy_dict_calibration_provenance_to_tfp_v1.py [--dry-run]
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "outputs" / "dict_calibration"
DEST_ROOT = REPO / "hesperia" / "modules" / "tfp" / "data" / "tfp_v1" / "provenance" / "api" / "runs"
DEST = DEST_ROOT / "outputs_dict_calibration_mirror"

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "[REDACTED_OPENAI_SK]"),
    (re.compile(r'(?i)("api_key"\s*:\s*")[^"]*(")'), r"\1[REDACTED]\2"),
    (re.compile(r'(?i)("authorization"\s*:\s*")[^"]*(")'), r"\1[REDACTED]\2"),
    (re.compile(r"(?i)Bearer\s+[A-Za-z0-9._\-]+"), "Bearer [REDACTED]"),
    (re.compile(r"(?i)OPENAI_API_KEY[=:]\s*\S+"), "OPENAI_API_KEY=[REDACTED]"),
]


def redact_text(raw: str) -> str:
    s = raw
    for pat, repl in _PATTERNS:
        s = pat.sub(repl, s)
    return s


def should_redact(path: Path) -> bool:
    return path.suffix.lower() in {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Mirror dict_calibration outputs into tfp_v1 provenance.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not SRC.is_dir():
        print(f"copy_dict_calibration_provenance: SKIP (no {SRC})", file=sys.stderr)
        return 0

    if args.dry_run:
        n = sum(1 for _ in SRC.rglob("*") if _.is_file())
        print(f"DRY-RUN: would copy ~{n} files -> {DEST}", file=sys.stderr)
        return 0

    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(SRC, DEST, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    n_red = 0
    for p in sorted(DEST.rglob("*")):
        if not p.is_file() or not should_redact(p):
            continue
        text = p.read_text(encoding="utf-8", errors="surrogateescape")
        new = redact_text(text)
        if new != text:
            p.write_text(new, encoding="utf-8", errors="surrogateescape")
            n_red += 1

    total = sum(1 for x in DEST.rglob("*") if x.is_file())
    b = sum(x.stat().st_size for x in DEST.rglob("*") if x.is_file())
    meta = {
        "copied_at": datetime.now(timezone.utc).isoformat(),
        "source": str(SRC.relative_to(REPO)),
        "destination": str(DEST.relative_to(REPO)),
        "file_count": total,
        "total_bytes": b,
        "redacted_text_files": n_red,
        "note": "TFP-DATA-T07 mirror; redaction best-effort per TFP_V1_PROVENANCE_API_POLICY.md; runs/ gitignored.",
    }
    man_path = REPO / "hesperia" / "modules" / "tfp" / "data" / "tfp_v1" / "provenance" / "api" / "COPY_MANIFEST_DICT_CALIBRATION.json"
    man_path.parent.mkdir(parents=True, exist_ok=True)
    man_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(
        f"copy_dict_calibration_provenance: OK files={total} bytes={b} redacted_files={n_red} -> {DEST}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
