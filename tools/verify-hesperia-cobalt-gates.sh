#!/usr/bin/env bash
# COBALT gates G1–G4 preflight before HESPERIA_COBALT_ENABLED=1 in prod.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${HESPERIA_PYTHON:-}"
if [[ -z "${PY}" && -x "${ROOT}/.venv/bin/python3" ]]; then
  PY="${ROOT}/.venv/bin/python3"
fi
PY="${PY:-python3}"

fail() { echo "COBALT GATE FAIL: $*" >&2; exit 1; }
ok() { echo "COBALT GATE OK: $*"; }

echo "=== COBALT G1 — CHROMA-2 reachable ==="
$PY - <<'PY' || fail "G1 CHROMA-2 unreachable"
import urllib.request
url = "http://chroma-2.prichindel.local:8002/api/v2/heartbeat"
with urllib.request.urlopen(url, timeout=8) as r:
    assert r.status == 200
print("heartbeat ok")
PY
ok "G1"

echo "=== COBALT G2 — Hesperia bounding on chunks (sample) ==="
$PY - <<'PY'
import chromadb
c = chromadb.HttpClient(host="chroma-2.prichindel.local", port=8002)
col = c.get_collection("documents")
part = col.get(limit=50, include=["metadatas"])
metas = part.get("metadatas") or []
with_cid = sum(1 for m in metas if m and m.get("concept_id"))
if with_cid < 5:
    raise SystemExit(f"G2 FAIL: only {with_cid}/50 chunks have concept_id")
print(f"G2 sample pass: {with_cid}/50 with concept_id")
PY
if [[ $? -ne 0 ]]; then
  echo "COBALT GATE WARN: G2 attribution incomplete — keep HESPERIA_COBALT_ENABLED=0"
  G2_FAIL=1
else
  ok "G2"
  G2_FAIL=0
fi

echo "=== COBALT G3 — pytest COBALT mock suite ==="
$PY -m pytest tests/cobalt/ -q
ok "G3 dev tests"

echo "=== COBALT G4 — facet scan (lang/library_layer) ==="
$PY - <<'PY' || fail "G4 facet scan"
import chromadb
c = chromadb.HttpClient(host="chroma-2.prichindel.local", port=8002)
col = c.get_collection("documents")
part = col.get(limit=200, include=["metadatas"])
langs = set()
for m in part.get("metadatas") or []:
    if m and m.get("lang"):
        langs.add(m["lang"])
if not langs:
    raise SystemExit("no lang facets in sample")
print("langs", sorted(langs)[:10])
PY
ok "G4 partial (lang facets present; theme=general until G2)"

if [[ "${G2_FAIL:-0}" -eq 1 ]]; then
  echo "=== SUMMARY: G1+G3+G4 dev OK; G2 blocks prod flag ==="
  exit 2
fi
echo "=== SUMMARY: G1–G4 PASS ==="
