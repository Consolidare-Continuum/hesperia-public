-- Phase 1 — tfp_corpus DDL (corpus only; no dict, no embeddings, no session tables).
-- Apply after 000_provision.sql as superuser (ops_method).
-- Ref: governance/SPEC-ETHAN-TFP-CORPUS-POSTGRES.md §2

BEGIN;

SET search_path TO tfp_corpus, public;

CREATE TABLE IF NOT EXISTS source_document (
    doc_id          text PRIMARY KEY,
    lang            text NOT NULL CHECK (lang IN ('ru','en')),
    corpus_pack     text NOT NULL,
    filename        text NOT NULL,
    title           text,
    author          text,
    content_hash    text NOT NULL,
    source_path     text NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT source_document_pack_chk CHECK (
      corpus_pack IN ('original', 'ru_2_cleaned', 'en_2_cleaned')
    )
);

CREATE TABLE IF NOT EXISTS document_chunk (
    chunk_id        text PRIMARY KEY,
    doc_id          text NOT NULL REFERENCES source_document(doc_id) ON DELETE CASCADE,
    chunk_index     int NOT NULL,
    text            text NOT NULL,
    char_count      int NOT NULL,
    fts_ru          tsvector GENERATED ALWAYS AS (to_tsvector('russian', text)) STORED,
    -- embedding    vector(768),  -- pgvector, SPEC §6 — not in v1
    UNIQUE (doc_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS document_chunk_fts_idx
  ON document_chunk USING gin (fts_ru);
CREATE INDEX IF NOT EXISTS document_chunk_trgm_idx
  ON document_chunk USING gin (text gin_trgm_ops);

CREATE TABLE IF NOT EXISTS ingest_run (
    run_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at      timestamptz NOT NULL DEFAULT now(),
    corpus_pack     text NOT NULL,
    files_seen      int NOT NULL,
    files_ingested  int NOT NULL,
    chunks_written  int NOT NULL,
    notes           text
);

CREATE OR REPLACE FUNCTION forbid_ingest_run_update()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'tfp_corpus.ingest_run is append-only';
END;
$$;

DROP TRIGGER IF EXISTS trg_ingest_run_no_update ON ingest_run;
CREATE TRIGGER trg_ingest_run_no_update
  BEFORE UPDATE OR DELETE ON ingest_run
  FOR EACH ROW EXECUTE FUNCTION forbid_ingest_run_update();

ALTER TABLE source_document OWNER TO tfp_corpus_rw;
ALTER TABLE document_chunk OWNER TO tfp_corpus_rw;
ALTER TABLE ingest_run OWNER TO tfp_corpus_rw;
ALTER FUNCTION forbid_ingest_run_update() OWNER TO tfp_corpus_rw;

GRANT USAGE ON SCHEMA tfp_corpus TO tfp_corpus_rw;
GRANT ALL ON ALL TABLES IN SCHEMA tfp_corpus TO tfp_corpus_rw;
GRANT ALL ON ALL SEQUENCES IN SCHEMA tfp_corpus TO tfp_corpus_rw;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA tfp_corpus TO tfp_corpus_rw;

ALTER DEFAULT PRIVILEGES FOR ROLE tfp_corpus_rw IN SCHEMA tfp_corpus
  GRANT ALL ON TABLES TO tfp_corpus_rw;

COMMIT;
