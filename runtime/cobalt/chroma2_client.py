# HESPERIA COBALT — CHROMA-2 query client (Papra documents collection).
from __future__ import annotations

import os
import urllib.error
import urllib.request
from typing import Any

os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")
try:
    import posthog

    posthog.capture = lambda *args, **kwargs: None
except Exception:
    pass

from runtime.cobalt.flags import chroma2_url

COLLECTION_NAME = "documents"
EMBEDDING_MODEL = os.environ.get(
    "CHROMA2_EMBEDDING_MODEL", "paraphrase-multilingual-mpnet-base-v2"
)

_embed_model = None


def _parse_host_port(url: str) -> tuple[str, int]:
    u = url.strip()
    if u.startswith("http://"):
        u = u[7:]
    elif u.startswith("https://"):
        u = u[8:]
    host, _, port_s = u.partition(":")
    return host or "127.0.0.1", int(port_s or "8002")


def heartbeat() -> dict[str, Any]:
    base = chroma2_url()
    for path in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
        try:
            req = urllib.request.Request(f"{base}{path}", method="GET")
            with urllib.request.urlopen(req, timeout=8) as resp:
                return {"ok": True, "path": path, "url": base}
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
    return {"ok": False, "url": base}


def _query_embedding(query_text: str) -> list[float]:
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer

        _embed_model = SentenceTransformer(EMBEDDING_MODEL)
    vector = _embed_model.encode([query_text], normalize_embeddings=True)
    return vector[0].tolist()


def query_chroma2(
    query_text: str,
    *,
    n_results: int = 5,
    lang: str | None = None,
    library_layer: str | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Return (hits, status) where status is ok|degraded|unavailable."""
    hb = heartbeat()
    if not hb.get("ok"):
        return [], "unavailable"
    try:
        import chromadb

        host, port = _parse_host_port(chroma2_url())
        client = chromadb.HttpClient(host=host, port=port)
        coll = client.get_collection(COLLECTION_NAME)
        kwargs: dict[str, Any] = {
            "query_embeddings": [_query_embedding(query_text)],
            "n_results": max(1, min(20, n_results)),
            "include": ["documents", "metadatas", "distances"],
        }
        where_clauses: list[dict[str, str]] = []
        if lang:
            where_clauses.append({"lang": lang.strip().lower()})
        if library_layer:
            where_clauses.append({"library_layer": library_layer.strip()})
        if len(where_clauses) == 1:
            kwargs["where"] = where_clauses[0]
        elif len(where_clauses) > 1:
            kwargs["where"] = {"$and": where_clauses}
        res = coll.query(**kwargs)
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        hits: list[dict[str, Any]] = []
        for rank, (doc, meta, dist) in enumerate(zip(docs, metas, dists), start=1):
            meta = meta or {}
            hits.append(
                {
                    "rank": rank,
                    "doc_id": meta.get("doc_id"),
                    "doc_name": meta.get("doc_name"),
                    "title": meta.get("title"),
                    "creator": meta.get("creator"),
                    "chunk_index": meta.get("chunk_index", meta.get("chunk")),
                    "excerpt": (doc or "")[:1200],
                    "distance": float(dist) if dist is not None else None,
                    "concept_id": meta.get("concept_id"),
                    "area_name": meta.get("area_name"),
                    "family_name": meta.get("family_name"),
                    "citation": f"{meta.get('doc_name') or meta.get('doc_id')}#{meta.get('chunk_index', '')}",
                }
            )
        return hits, "ok" if hits else "degraded"
    except Exception:
        return [], "degraded"
