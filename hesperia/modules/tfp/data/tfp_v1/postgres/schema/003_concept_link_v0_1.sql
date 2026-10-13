-- Phase 4a — concept_link DDL (structural wiring: dict_a/dict_b -> corpus, inside Postgres).
-- Apply after 002_normalized_sentence_v0_1.sql as superuser (ops_method).
-- Ref: docs/recipes/chiron_tweaks/BACKLOG.md ("normalized corpus" investigation, 2026-08-19)
--
-- Deterministic, free, local: runs the SAME match_dict_a()/resolve_hit() matcher already used
-- in production (core/engine/lexical_concept/pipeline.py) against every row in
-- normalized_sentence and document_chunk (corpus_pack='original' only -- ru_2_cleaned/
-- en_2_cleaned are the same content, see §4 of SPEC-ETHAN-TFP-CORPUS-POSTGRES.md). Links text to
-- TFP structure (concept/family/area) directly, not via document metadata (pages/authors/
-- chapters) -- structural indexing per operator instruction, 2026-08-19.
--
-- Fully derived/deterministic: same inputs -> same output. Rebuilt by TRUNCATE + re-insert each
-- run (link_corpus_to_structure.py), not incrementally patched -- consistent with this project's
-- "fresh reruns over stale checked-in artifacts" convention.

BEGIN;

SET search_path TO tfp_corpus, public;

CREATE TABLE IF NOT EXISTS concept_link (
    link_id         bigserial PRIMARY KEY,
    source_kind     text NOT NULL CHECK (source_kind IN ('sentence', 'chunk')),
    source_id       text NOT NULL,   -- normalized_sentence.sentence_id::text or document_chunk.chunk_id
    lang            text NOT NULL CHECK (lang IN ('ru','en')),
    concept_id      text NOT NULL,
    family_id       text,
    area_id         text,
    match_type      text NOT NULL,   -- exact/phrase/lemma/stem/pattern (from LexicalHit)
    matched_text    text NOT NULL,
    entry_id        text NOT NULL,   -- dict_a entry_id that produced the hit
    activation      double precision NOT NULL,  -- resolve_hit()'s winning candidate score
    dict_version    text NOT NULL,   -- HESPERIA_CALIB_DICT_VERSION used for this run
    linked_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS concept_link_source_idx
  ON concept_link (source_kind, source_id);
CREATE INDEX IF NOT EXISTS concept_link_concept_idx
  ON concept_link (concept_id);
CREATE INDEX IF NOT EXISTS concept_link_family_idx
  ON concept_link (family_id);
CREATE INDEX IF NOT EXISTS concept_link_area_idx
  ON concept_link (area_id);

ALTER TABLE concept_link OWNER TO tfp_corpus_rw;

GRANT ALL ON ALL TABLES IN SCHEMA tfp_corpus TO tfp_corpus_rw;
GRANT ALL ON ALL SEQUENCES IN SCHEMA tfp_corpus TO tfp_corpus_rw;

COMMIT;
