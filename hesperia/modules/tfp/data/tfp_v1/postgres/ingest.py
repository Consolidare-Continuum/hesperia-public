#!/usr/bin/env python3
"""TFP corpus -> tfp_corpus schema (Phase 2). Ref: governance/SPEC-ETHAN-TFP-CORPUS-POSTGRES.md.

Reads corpus_pack in {original, ru_2_cleaned, en_2_cleaned} from local files on disk
(pulled from prichindel's canonical corpus tree; these are gitignored, local-only), chunks
them the same way agent_mcp_knowledge.ingest.chunk_text does (same params, reimplemented
locally to avoid a cross-repo runtime dependency), and writes source_document/document_chunk/
ingest_run rows. Idempotent per file via content_hash: unchanged files are skipped, changed
files replace their prior chunks.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

import psycopg2

DSN = dict(host="127.0.0.1", port=5433, dbname="ops_method", user="tfp_corpus_rw", password="tfp_corpus_dev")

CORPUS_ROOT = Path(__file__).resolve().parent.parent / "corpus"  # tfp_v1/postgres/../corpus

# corpus_pack -> (lang, dir, skip filenames)
PACKS: dict[str, tuple[str, Path, frozenset[str]]] = {
    "original_ru": ("ru", CORPUS_ROOT / "original/ru", frozenset({"CORPUS_MD_TREE_RU.md", "_cleanup_report.json"})),
    "original_en": ("en", CORPUS_ROOT / "original/en", frozenset()),
    "ru_2_cleaned": ("ru", CORPUS_ROOT / "ru_2_cleaned", frozenset({"CORPUS_MD_TREE_RU.md", "_cleanup_report.json"})),
    "en_2_cleaned": ("en", CORPUS_ROOT / "en_2_cleaned", frozenset()),
}
# DB corpus_pack value per key above (original_ru/original_en both map to 'original')
PACK_DB_VALUE = {"original_ru": "original", "original_en": "original", "ru_2_cleaned": "ru_2_cleaned", "en_2_cleaned": "en_2_cleaned"}

MAX_CHARS = 1200
OVERLAP = 100


def chunk_text(text: str) -> list[str]:
    """Same algorithm/params as agent_mcp_knowledge.ingest.chunk_text (brain repo), reimplemented
    locally so this script has no cross-repo dependency. Keep in sync if that one changes."""
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"\n\n+|\n(?=## )", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if current_len + len(p) + 2 <= MAX_CHARS:
            current.append(p)
            current_len += len(p) + 2
        else:
            if current:
                chunks.append("\n\n".join(current))
            if len(p) > MAX_CHARS:
                for i in range(0, len(p), MAX_CHARS - OVERLAP):
                    seg = p[i : i + MAX_CHARS]
                    if seg.strip():
                        chunks.append(seg.strip())
                current = []
                current_len = 0
            else:
                overlap_text = "\n\n".join(current)[-OVERLAP:] if current and OVERLAP else ""
                current = [overlap_text + p] if overlap_text else [p]
                current_len = len(current[0])
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def sanitize_doc_id(filename: str, pack: str) -> str:
    stem = re.sub(r"\.md$", "", filename)
    stem = re.sub(r"[^A-Za-z0-9А-Яа-яЁё_.\-]+", "_", stem)
    return f"{pack}__{stem}"[:250]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ingest_pack(cur, pack_key: str, dry_run: bool) -> tuple[int, int, int]:
    lang, src_dir, skip = PACKS[pack_key]
    db_pack = PACK_DB_VALUE[pack_key]
    if not src_dir.is_dir():
        print(f"SKIP {pack_key}: {src_dir} not present locally")
        return (0, 0, 0)
    files = sorted(p for p in src_dir.glob("*.md") if p.name not in skip)
    files_seen = len(files)
    files_ingested = 0
    chunks_written = 0
    for path in files:
        doc_id = sanitize_doc_id(path.name, pack_key)
        content_hash = sha256_file(path)
        cur.execute("SELECT content_hash FROM tfp_corpus.source_document WHERE doc_id = %s", (doc_id,))
        row = cur.fetchone()
        if row is not None and row[0] == content_hash:
            continue  # unchanged, skip
        text = path.read_text(encoding="utf-8", errors="replace")
        chunks = chunk_text(text)
        if dry_run:
            files_ingested += 1
            chunks_written += len(chunks)
            continue
        if row is not None:
            cur.execute("DELETE FROM tfp_corpus.source_document WHERE doc_id = %s", (doc_id,))
        cur.execute(
            """INSERT INTO tfp_corpus.source_document
               (doc_id, lang, corpus_pack, filename, content_hash, source_path)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (doc_id, lang, db_pack, path.name, content_hash, str(path)),
        )
        for idx, chunk in enumerate(chunks):
            cur.execute(
                """INSERT INTO tfp_corpus.document_chunk
                   (chunk_id, doc_id, chunk_index, text, char_count)
                   VALUES (%s, %s, %s, %s, %s)""",
                (f"{doc_id}_{idx}", doc_id, idx, chunk, len(chunk)),
            )
        files_ingested += 1
        chunks_written += len(chunks)
    return (files_seen, files_ingested, chunks_written)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", choices=list(PACKS) + ["all"], default="all")
    ap.add_argument("--dry-run", action="store_true", help="Count only, no DB writes")
    args = ap.parse_args()

    pack_keys = list(PACKS) if args.pack == "all" else [args.pack]
    conn = psycopg2.connect(**DSN)
    conn.autocommit = False
    try:
        cur = conn.cursor()
        totals = {"seen": 0, "ingested": 0, "chunks": 0}
        by_db_pack: dict[str, list[int]] = {}
        for key in pack_keys:
            seen, ingested, chunks = ingest_pack(cur, key, args.dry_run)
            print(f"{key}: files_seen={seen} files_ingested={ingested} chunks_written={chunks}")
            totals["seen"] += seen
            totals["ingested"] += ingested
            totals["chunks"] += chunks
            db_pack = PACK_DB_VALUE[key]
            acc = by_db_pack.setdefault(db_pack, [0, 0, 0])
            acc[0] += seen
            acc[1] += ingested
            acc[2] += chunks
        if not args.dry_run:
            for db_pack, (seen, ingested, chunks) in by_db_pack.items():
                cur.execute(
                    """INSERT INTO tfp_corpus.ingest_run
                       (corpus_pack, files_seen, files_ingested, chunks_written, notes)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (db_pack, seen, ingested, chunks, f"ingest.py --pack {args.pack}"),
                )
            conn.commit()
        else:
            conn.rollback()
        print(f"TOTAL: files_seen={totals['seen']} files_ingested={totals['ingested']} chunks_written={totals['chunks']}"
              + (" (dry-run, not committed)" if args.dry_run else ""))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
