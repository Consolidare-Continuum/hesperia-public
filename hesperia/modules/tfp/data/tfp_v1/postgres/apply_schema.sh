#!/usr/bin/env bash
# Apply tfp_corpus Phase 0/1 into existing ops-method-pg (127.0.0.1:5433).
# Does not start a new Postgres. Does not ingest corpus. Does not touch schema ops_method.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CONTAINER="${TFP_PG_CONTAINER:-ops-method-pg}"
PGUSER="${TFP_PG_SUPERUSER:-ops_method}"
PGDATABASE="${TFP_PG_DATABASE:-ops_method}"

if ! docker inspect -f '{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null | grep -q healthy; then
  echo "FAILED: container $CONTAINER not healthy" >&2
  exit 2
fi

for f in "$ROOT/schema/000_provision.sql" "$ROOT/schema/001_source_corpus_v0_1.sql"; do
  echo "APPLY $(basename "$f")"
  docker exec -i "$CONTAINER" psql -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 <"$f"
done

echo "VERIFY"
docker exec -i "$CONTAINER" psql -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 <<'SQL'
SELECT nspname FROM pg_namespace WHERE nspname = 'tfp_corpus';
SELECT rolname FROM pg_roles WHERE rolname = 'tfp_corpus_rw';
SELECT c.relname
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'tfp_corpus' AND c.relkind = 'r'
 ORDER BY 1;
SELECT count(*) AS ops_method_tables
  FROM information_schema.tables
 WHERE table_schema = 'ops_method';
SQL
