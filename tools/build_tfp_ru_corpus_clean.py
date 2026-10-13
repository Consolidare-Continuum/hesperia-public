#!/usr/bin/env python3
# HESPERIA — RAD. TASK 2: normalize research/_noone_local/2_cleaned → sentence JSONL.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Emit ``corpora/tfp_ru_cleaned_sentences.jsonl`` with lines ``{\"text\": \"...\"}``.

Heuristics: strip obvious bibliography/OCR lines, lowercase, unify quotes/dashes.
Does not claim completeness; human review recommended before gold tagging.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SRC = REPO / "research" / "_noone_local" / "2_cleaned"
DEFAULT_OUT = (
    REPO / "assets" / "data" / "engine_dynamics_v060" / "corpora" / "tfp_ru_cleaned_sentences.jsonl"
)

SKIP_LINE = re.compile(
    r"^(библиография|references|doi:|http://|https://|страница\s+\d+|^\d+\s*$|удк\s|ббк\s)",
    re.I,
)
SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def clean_block(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in t.split("\n"):
        s = line.strip()
        if not s or SKIP_LINE.search(s):
            continue
        if re.match(r"^#{1,6}\s", s):
            continue
        lines.append(s)
    blob = " ".join(lines)
    blob = re.sub(r"[ \t]+", " ", blob)
    blob = blob.replace("«", '"').replace("»", '"').replace("’", "'").replace("—", "-")
    return blob.strip().lower()


def sentences_from_blob(blob: str) -> list[str]:
    if not blob:
        return []
    parts = SENT_SPLIT.split(blob)
    out = []
    for p in parts:
        p = p.strip()
        if len(p) > 20:
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if not args.src.is_dir():
        print(f"ERROR: source dir missing: {args.src}")
        return 2
    all_sents: list[str] = []
    for md in sorted(args.src.glob("*.md")):
        raw = md.read_text(encoding="utf-8", errors="replace")
        blob = clean_block(raw)
        all_sents.extend(sentences_from_blob(blob))
    # Dedupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for s in all_sents:
        if s in seen:
            continue
        seen.add(s)
        uniq.append(s)
    print(f"sentences={len(uniq)} from {args.src}")
    if not args.write:
        print("Dry run. Pass --write to write JSONL.")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for s in uniq:
            f.write(json.dumps({"text": s}, ensure_ascii=False) + "\n")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
