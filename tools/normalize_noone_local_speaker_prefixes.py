#!/usr/bin/env python3
# HESPERIA — RAD. Normalize Т./П. dialogue prefixes in top-level _noone_local/*.md
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Replace line-initial therapist/patient shorthand with explicit labels:

  Т. ...  → Терапевт: ...
  П. ...  → Пациент: ...

Handles numbered turns (Т.22. …, П.17.Как …), missing space after dot (Т.С …, П.Нет …).
Skips lines starting with «т.е.» (Т.е.).

Only files directly under research/_noone_local/ (not subdirs).

Dry-run:  python3 tools/normalize_noone_local_speaker_prefixes.py
Apply:    python3 tools/normalize_noone_local_speaker_prefixes.py --write
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOONE = REPO / "research" / "_noone_local"


def normalize_line(line: str) -> str:
    m = re.match(r"^(\s*)([^\n\r]*)(\r?\n?)$", line)
    if not m:
        return line
    ws, body, ending = m.group(1), m.group(2), m.group(3)
    if not body:
        return line

    if body.startswith("T.") and re.match(r"^T\.\s", body):
        return ws + re.sub(r"^T\.\s+", "Терапевт: ", body, count=1) + ending
    if body.startswith("P.") and re.match(r"^P\.\s", body):
        return ws + re.sub(r"^P\.\s+", "Пациент: ", body, count=1) + ending

    if re.match(r"^Т\.е\.\s", body):
        return line

    if body.startswith("Т."):
        if re.match(r"^Т\.\d+\.", body):
            return ws + "Терапевт: " + body[2:] + ending
        if re.match(r"^Т\.\s", body):
            return ws + "Терапевт: " + body[2:].lstrip() + ending
        if re.match(r"^Т\.[А-ЯЁA-Za-z?]", body):
            return ws + "Терапевт: " + body[2:] + ending

    if body.startswith("П."):
        if re.match(r"^П\.\d+\.", body):
            core = body[2:]
            mnum = re.match(r"^(\d+\.)(\s*)(.*)$", core)
            if mnum:
                num, sp, tail = mnum.group(1), mnum.group(2), mnum.group(3)
                if not sp and tail and tail[0] not in " \t":
                    return ws + f"Пациент: {num} {tail}" + ending
                return ws + f"Пациент: {num}{sp}{tail}" + ending
        if re.match(r"^П\.\s", body):
            return ws + "Пациент: " + body[2:].lstrip() + ending
        if re.match(r"^П\.[А-ЯЁA-Za-z?0-9]", body):
            return ws + "Пациент: " + body[2:] + ending

    return line


def process_file(path: Path, *, write: bool) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    new_lines = [normalize_line(L) for L in lines]
    new_text = "".join(new_lines)
    changed = sum(1 for a, b in zip(lines, new_lines) if a != b)
    if write and new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return changed, len(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    md_files = sorted(p for p in NOONE.iterdir() if p.is_file() and p.suffix.lower() == ".md")
    if not md_files:
        print(f"No top-level .md under {NOONE}")
        return 1

    total_changes = 0
    for p in md_files:
        n, nlines = process_file(p, write=args.write)
        if n:
            total_changes += n
            print(f"{'WROTE' if args.write else 'WOULD'} {p.name}: {n} line(s) / {nlines}")
    print(f"Done. Lines touched: {total_changes} across {len(md_files)} file(s).")
    if not args.write and total_changes:
        print("Pass --write to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
