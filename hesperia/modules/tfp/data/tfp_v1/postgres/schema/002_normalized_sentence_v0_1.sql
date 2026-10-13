-- Phase 3 — normalized_sentence DDL (real TASK-2 cleaned corpus, provenance-less by design).
-- Apply after 001_source_corpus_v0_1.sql as superuser (ops_method).
-- Ref: docs/recipes/chiron_tweaks/BACKLOG.md ("normalized corpus" investigation, 2026-08-19)
--
-- This is NOT the ru_2_cleaned/en_2_cleaned corpus_pack in source_document -- those are
-- confirmed content-identical to `original` (checked live in this DB, in the 2026-03-24
-- backup tarball, and in Papra's own dedupe log -- all three agree). For any structural
-- grounding that needs a real document tree, use corpus_pack='original'; ru_2_cleaned/
-- en_2_cleaned are duplicates of it, not a separate normalized source.
--
-- This table holds the one artifact that IS real normalization: `tools/
-- build_tfp_ru_corpus_clean.py`'s TASK-2 output (2026-03-20), 16826 RU sentences --
-- lowercased, bibliography/OCR-stripped, sentence-split, globally deduped. The source
-- script's own global dedup destroyed per-file boundaries, so there is no doc_id to
-- attach these to -- intentionally no FK to source_document. Structural linkage (which
-- TFP area/family/concept a sentence activates) is meant to come later via the ACB
-- pipeline (tools/dict_calibration/ru_tfp_corpus_align.py), not via document metadata.

BEGIN;

SET search_path TO tfp_corpus, public;

CREATE TABLE IF NOT EXISTS normalized_sentence (
    sentence_id     bigserial PRIMARY KEY,
    lang            text NOT NULL CHECK (lang IN ('ru','en')),
    text            text NOT NULL,
    char_count      int NOT NULL,
    source_artifact text NOT NULL,   -- e.g. 'tfp_ru_cleaned_sentences.jsonl'
    source_hash     text NOT NULL,   -- sha256 of the source artifact at ingest time
    fts_ru          tsvector GENERATED ALWAYS AS (to_tsvector('russian', text)) STORED,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (lang, text)
);

CREATE INDEX IF NOT EXISTS normalized_sentence_fts_idx
  ON normalized_sentence USING gin (fts_ru);
CREATE INDEX IF NOT EXISTS normalized_sentence_trgm_idx
  ON normalized_sentence USING gin (text gin_trgm_ops);

ALTER TABLE normalized_sentence OWNER TO tfp_corpus_rw;

GRANT ALL ON ALL TABLES IN SCHEMA tfp_corpus TO tfp_corpus_rw;
GRANT ALL ON ALL SEQUENCES IN SCHEMA tfp_corpus TO tfp_corpus_rw;

COMMIT;
