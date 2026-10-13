#!/usr/bin/env python3
"""normalized_sentence + document_chunk(original) -> tfp_corpus.concept_link (Phase 4a).

Ref: docs/recipes/chiron_tweaks/BACKLOG.md ("normalized corpus" investigation, 2026-08-19).

Deterministic, free, local: runs the same match_dict_a()/resolve_hit() matcher already used in
production (core/engine/lexical_concept/pipeline.py) against every row, using the sealed
production dict (HESPERIA_CALIB_DICT_VERSION=v0_6_0_clr_v052_5 -- the pack already auto-pinned
for the tfp profile). No max_accepted cap here: unlike the live analyze path, this is building a
structural index, not scoring a single session against a fixed budget -- full coverage is the
point. Reads family_id/area_id straight from the matched dict_b row's family_ids/area_ids
(present on every concept regardless of concept_id naming style), not from ID-string parsing.

Fully derived: TRUNCATEs concept_link at the start of every run, per this project's "fresh reruns
over stale artifacts" convention -- this is not incremental.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

_REPO = Path(__file__).resolve().parents[6]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.lexical.matcher import match_dict_a  # noqa: E402
from core.pipeline.lexical import normalize_text  # noqa: E402
from core.pipeline.resolver import resolve_hit  # noqa: E402
from hesperia.engine.calibration_dict_paths import resolve_dict_file  # noqa: E402

DSN = dict(host="127.0.0.1", port=5433, dbname="ops_method", user="tfp_corpus_rw", password="tfp_corpus_dev")
DICT_VERSION = os.environ.get("HESPERIA_CALIB_DICT_VERSION", "v0_6_0_clr_v052_5")

# Same default stopword set as core/engine/lexical_concept/pipeline.py's
# _DEFAULT_STOPWORDS -- without this, short function words (prepositions,
# conjunctions) spuriously match single-token dict_a entries and flood the
# index with noise (e.g. "в" -> B_A10_F11_002, "и" -> B_A1_F19_003).
_STOPWORDS = frozenset({"и", "в", "на", "с", "к", "по", "но", "а", "я", "он", "мы"})
_MIN_TOKEN_LEN = 3


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_dicts() -> tuple[list[dict], dict[str, dict]]:
    a_path = resolve_dict_file(_REPO, "dict_a.jsonl", explicit_version=DICT_VERSION)
    b_path = resolve_dict_file(_REPO, "dict_b.jsonl", explicit_version=DICT_VERSION)
    if not a_path or not b_path:
        raise SystemExit(f"ERROR: sealed dict pack not found for version={DICT_VERSION}")
    dict_a = _load_jsonl(a_path)
    dict_b_rows = _load_jsonl(b_path)
    concept_index: dict[str, dict] = {}
    for row in dict_b_rows:
        cid = str(row.get("concept_id") or "")
        if cid and cid not in concept_index:
            concept_index[cid] = row
    print(f"dict_a: {len(dict_a)} entries; dict_b: {len(concept_index)} unique concepts (from {b_path})")
    return dict_a, concept_index


def link_text(
    text: str,
    dict_a: list[dict],
    concept_index: dict[str, dict],
) -> list[tuple[str, str, str, str, str, str, float]]:
    """Returns rows: (concept_id, family_id, area_id, match_type, matched_text, entry_id, activation)."""
    norm = normalize_text(text)
    ct = norm["canonical_text"]
    hits, _rejected = match_dict_a(ct, dict_a)  # no max_accepted: full coverage for indexing
    out: list[tuple[str, str, str, str, str, str, float]] = []
    for hit in hits:
        mt = hit.matched_text.strip().casefold()
        if len(mt) < _MIN_TOKEN_LEN or mt in _STOPWORDS:
            continue
        r = resolve_hit(hit, concept_index, canonical_text=ct)
        winner = r.get("winning_concept_id")
        if not winner:
            continue
        concept = concept_index.get(str(winner), {})
        family_ids = concept.get("family_ids") or []
        area_ids = concept.get("area_ids") or []
        family_id = str(family_ids[0]) if family_ids else ""
        area_id = str(area_ids[0]) if area_ids else ""
        score = float((r.get("candidate_scores") or {}).get(str(winner), 0.0))
        out.append((str(winner), family_id, area_id, hit.match_type, hit.matched_text, hit.entry_id, score))
    return out


def main() -> int:
    dict_a, concept_index = load_dicts()

    conn = psycopg2.connect(**DSN)
    conn.autocommit = False
    try:
        cur = conn.cursor()
        cur.execute("TRUNCATE tfp_corpus.concept_link")

        # --- sentences ---
        cur.execute("SELECT sentence_id, lang, text FROM tfp_corpus.normalized_sentence ORDER BY sentence_id")
        rows_written = 0
        batch: list[tuple] = []
        for sentence_id, lang, text in cur.fetchall():
            for concept_id, family_id, area_id, match_type, matched_text, entry_id, score in link_text(
                text, dict_a, concept_index
            ):
                batch.append(
                    ("sentence", str(sentence_id), lang, concept_id, family_id, area_id,
                     match_type, matched_text, entry_id, score, DICT_VERSION)
                )
            if len(batch) >= 5000:
                execute_values(
                    cur,
                    """INSERT INTO tfp_corpus.concept_link
                       (source_kind, source_id, lang, concept_id, family_id, area_id,
                        match_type, matched_text, entry_id, activation, dict_version)
                       VALUES %s""",
                    batch,
                )
                rows_written += len(batch)
                batch = []
        if batch:
            execute_values(
                cur,
                """INSERT INTO tfp_corpus.concept_link
                   (source_kind, source_id, lang, concept_id, family_id, area_id,
                    match_type, matched_text, entry_id, activation, dict_version)
                   VALUES %s""",
                batch,
            )
            rows_written += len(batch)
            batch = []
        print(f"sentences: linked {rows_written} concept_link rows")

        # --- document chunks (corpus_pack='original' only, per SPEC §4) ---
        cur.execute(
            """SELECT c.chunk_id, d.lang, c.text
               FROM tfp_corpus.document_chunk c
               JOIN tfp_corpus.source_document d ON d.doc_id = c.doc_id
               WHERE d.corpus_pack = 'original'
               ORDER BY c.chunk_id"""
        )
        chunk_rows_written = 0
        for chunk_id, lang, text in cur.fetchall():
            for concept_id, family_id, area_id, match_type, matched_text, entry_id, score in link_text(
                text, dict_a, concept_index
            ):
                batch.append(
                    ("chunk", str(chunk_id), lang, concept_id, family_id, area_id,
                     match_type, matched_text, entry_id, score, DICT_VERSION)
                )
            if len(batch) >= 5000:
                execute_values(
                    cur,
                    """INSERT INTO tfp_corpus.concept_link
                       (source_kind, source_id, lang, concept_id, family_id, area_id,
                        match_type, matched_text, entry_id, activation, dict_version)
                       VALUES %s""",
                    batch,
                )
                chunk_rows_written += len(batch)
                batch = []
        if batch:
            execute_values(
                cur,
                """INSERT INTO tfp_corpus.concept_link
                   (source_kind, source_id, lang, concept_id, family_id, area_id,
                    match_type, matched_text, entry_id, activation, dict_version)
                   VALUES %s""",
                batch,
            )
            chunk_rows_written += len(batch)
        print(f"chunks: linked {chunk_rows_written} concept_link rows")

        conn.commit()
        print(f"TOTAL concept_link rows: {rows_written + chunk_rows_written}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
