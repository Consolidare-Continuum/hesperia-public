"""Postgres-backed semantic support (S) and corpus-authority weight (W) for the
contradiction-grounding "truth-point" score.

Ref: governance/SPEC-ETHAN-TFP-CORPUS-POSTGRES.md, inbox.md 2026-08-18 (two-channel
truth-point task). CHROMA-2 stays untouched -- this queries `tfp_corpus` (full-text
search against the 274-file/49,322-chunk corpus ingested there) instead.

Full-text (`fts_ru`/`ts_rank_cd`), not trigram: tried `word_similarity()` first (the
GIN trigram index makes the WHERE clause fast, ~10ms) but the actual scoring over the
thousands of loosely-matching candidate rows it returns took ~4s *per concept* -- with
~30-100 distinct concepts per real session that's minutes, not milliseconds. Russian FTS
does real lexeme stemming (matches inflected forms properly, unlike trigram's raw
character overlap) and is ~100x faster in practice (~35ms), because `@@` is a real
boolean index condition, not a fuzzy-scored bitmap scan. Confirmed via EXPLAIN ANALYZE
on the live corpus before choosing this, not assumed.

Degrades safely: if Postgres is unreachable, or a concept has no dict_b label, every
concept gets S=0/W=0 (so T = L, i.e. behaves exactly like before this module existed) --
same fail-open posture as runtime/cobalt/chroma2_client.py's CHROMA-2 path.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import psycopg2
except ImportError:  # pragma: no cover - psycopg2 not installed
    psycopg2 = None  # type: ignore[assignment]

DSN: dict[str, Any] = dict(host="127.0.0.1", port=5433, dbname="ops_method", user="tfp_corpus_rw", password="tfp_corpus_dev")
TOP_K = 20
# ts_rank_cd normalization flag 32: rank / (rank + 1) -- maps the otherwise-unbounded
# rank into [0, 1) so it's directly usable as S. Standard Postgres FTS idiom for this.
RANK_NORMALIZATION = 32
AUTHORITY_FULL_TRUST_DOCS = 3  # W saturates once this many distinct documents support a concept


def load_concept_labels(dict_b_path: Path | None) -> dict[str, str]:
    """concept_id -> first non-empty preferred_label seen in dict_b.jsonl (RU/EN as stored)."""
    labels: dict[str, str] = {}
    if dict_b_path is None or not dict_b_path.is_file():
        return labels
    with dict_b_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = row.get("concept_id")
            label = row.get("preferred_label")
            if cid and label and cid not in labels:
                labels[cid] = label
    return labels


def corpus_support(concept_ids: set[str], dict_b_path: Path | None) -> dict[str, dict[str, Any]]:
    """For each concept_id: {"S": float in [0,1), "W": float in [0,1], "status": str}.

    S = best ts_rank_cd (Russian FTS, normalized) between the concept's dict_b label
    and any corpus chunk that lexeme-matches it. W = min(1, distinct matching
    source_document count / AUTHORITY_FULL_TRUST_DOCS) -- the corpus's own redundancy
    across independent documents standing in for an authority weight, since
    per-document author metadata isn't populated (SPEC §4).
    """
    result: dict[str, dict[str, Any]] = {cid: {"S": 0.0, "W": 0.0, "status": "unavailable"} for cid in concept_ids}
    if psycopg2 is None:
        return result
    labels = load_concept_labels(dict_b_path)
    if not any(cid in labels for cid in concept_ids):
        # Nothing to look up -- skip the DB round-trip entirely (also keeps unit
        # tests that don't pass dict_b_path from making a real network connection).
        for cid in concept_ids:
            result[cid] = {"S": 0.0, "W": 0.0, "status": "no_label"}
        return result
    try:
        conn = psycopg2.connect(connect_timeout=3, **DSN)
    except Exception:
        return result
    try:
        cur = conn.cursor()
        for cid in concept_ids:
            label = labels.get(cid)
            if not label:
                result[cid] = {"S": 0.0, "W": 0.0, "status": "no_label"}
                continue
            try:
                cur.execute(
                    """SELECT dc.doc_id, ts_rank_cd(dc.fts_ru, plainto_tsquery('russian', %(q)s), %(norm)s) AS rank
                       FROM tfp_corpus.document_chunk dc
                       WHERE dc.fts_ru @@ plainto_tsquery('russian', %(q)s)
                       ORDER BY rank DESC LIMIT %(k)s""",
                    {"q": label, "norm": RANK_NORMALIZATION, "k": TOP_K},
                )
                rows = cur.fetchall()
            except Exception:
                conn.rollback()
                result[cid] = {"S": 0.0, "W": 0.0, "status": "query_error"}
                continue
            if not rows:
                result[cid] = {"S": 0.0, "W": 0.0, "status": "ok"}
                continue
            best_rank = max(rank for _, rank in rows if rank is not None)
            distinct_docs = len({doc_id for doc_id, _ in rows})
            w = min(1.0, distinct_docs / AUTHORITY_FULL_TRUST_DOCS)
            result[cid] = {"S": round(float(best_rank), 6), "W": round(float(w), 6), "status": "ok"}
    finally:
        conn.close()
    return result
