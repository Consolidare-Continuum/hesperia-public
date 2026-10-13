#!/usr/bin/env python3
"""tfp_ru_cleaned_sentences.jsonl -> tfp_corpus.normalized_sentence (Phase 3).

Ref: docs/recipes/chiron_tweaks/BACKLOG.md ("normalized corpus" investigation, 2026-08-19).

The source JSONL has no per-sentence provenance (its own builder, tools/
build_tfp_ru_corpus_clean.py, globally dedupes across all source files before writing,
destroying the file boundary) -- so this writes flat rows with no doc_id FK, relying on
UNIQUE (lang, text) for idempotency instead of a per-file content_hash check.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import psycopg2

DSN = dict(host="127.0.0.1", port=5433, dbname="ops_method", user="tfp_corpus_rw", password="tfp_corpus_dev")

DEFAULT_SRC = (
    Path(__file__).resolve().parents[6]
    / "assets/data/engine_dynamics_v060/corpora/tfp_ru_cleaned_sentences.jsonl"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.src.is_file():
        print(f"ERROR: source missing: {args.src}")
        return 2

    raw = args.src.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    lines = raw.decode("utf-8").splitlines()

    rows: list[tuple[str, str, int, str, str]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        text = obj.get("text", "").strip()
        if not text:
            continue
        rows.append((args.lang, text, len(text), args.src.name, source_hash))

    print(f"parsed {len(rows)} sentences from {args.src} (sha256={source_hash[:12]}...)")
    if args.dry_run:
        print("dry-run, not writing")
        return 0

    conn = psycopg2.connect(**DSN)
    conn.autocommit = False
    try:
        cur = conn.cursor()
        inserted = 0
        for lang, text, char_count, source_artifact, src_hash in rows:
            cur.execute(
                """INSERT INTO tfp_corpus.normalized_sentence
                   (lang, text, char_count, source_artifact, source_hash)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (lang, text) DO NOTHING""",
                (lang, text, char_count, source_artifact, src_hash),
            )
            inserted += cur.rowcount
        conn.commit()
        print(f"inserted {inserted} new rows ({len(rows) - inserted} already present)")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
