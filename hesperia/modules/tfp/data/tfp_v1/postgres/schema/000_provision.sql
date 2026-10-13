-- Phase 0 — provision tfp_corpus schema + role inside existing ops-method-pg.
-- Instance: 127.0.0.1:5433 database ops_method. Does NOT touch schema ops_method.
-- Local-dev password posture matches ops-method-pg (loopback only).
-- Ref: governance/SPEC-ETHAN-TFP-CORPUS-POSTGRES.md

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tfp_corpus_rw') THEN
    CREATE ROLE tfp_corpus_rw LOGIN PASSWORD 'tfp_corpus_dev';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE ops_method TO tfp_corpus_rw;

CREATE SCHEMA IF NOT EXISTS tfp_corpus AUTHORIZATION tfp_corpus_rw;

ALTER ROLE tfp_corpus_rw SET search_path TO tfp_corpus, public;

GRANT USAGE ON SCHEMA public TO tfp_corpus_rw;
REVOKE ALL ON SCHEMA ops_method FROM tfp_corpus_rw;

COMMIT;
