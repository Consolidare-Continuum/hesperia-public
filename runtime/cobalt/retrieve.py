# HESPERIA COBALT — compose_and_retrieve entry (spec §3.1).
from __future__ import annotations

from typing import Any, Literal

from runtime.cobalt.chroma2_client import query_chroma2
from runtime.cobalt.flags import cobalt_top_k

Strategy = Literal["S0", "S1", "S2", "S3"]


def _compose_query(
    text: str,
    engine_result: dict[str, Any] | None,
    *,
    strategy: Strategy = "S1",
) -> str:
    base = (text or "").strip()
    if strategy == "S0" or not engine_result:
        return base
    trace = engine_result.get("trace") if isinstance(engine_result, dict) else None
    if not isinstance(trace, dict):
        return base
    area = trace.get("dominant_area_id") or trace.get("area_id")
    fam = trace.get("dominant_family_id") or trace.get("family_id")
    parts = [base]
    if area is not None:
        parts.append(f"area:{area}")
    if fam is not None:
        parts.append(f"family:{fam}")
    return " ".join(p for p in parts if p).strip() or base


def compose_and_retrieve(
    text: str,
    *,
    engine_url: str | None = None,
    chroma_url: str | None = None,
    engine_result: dict[str, Any] | None = None,
    strategy: Strategy = "S1",
    branch: str | None = None,
    lang: str | None = None,
    top_k: int | None = None,
) -> dict[str, Any]:
    """Build cobalt_retrieval v0.1-mvp packet. engine_url/chroma_url reserved for future HTTP split."""
    _ = engine_url, chroma_url
    k = top_k if top_k is not None else cobalt_top_k()
    composed = _compose_query(text, engine_result, strategy=strategy)
    hits, status = query_chroma2(composed, n_results=k, lang=lang)
    return {
        "version": "0.1-mvp",
        "branch": branch,
        "store_primary": "CHROMA-2",
        "query_composed": composed,
        "strategy": strategy,
        "filters": {"lang": lang, "library_layer": None, "concept_id": None, "area_name": None, "family_name": None},
        "hits": hits,
        "retrieval_meta": {
            "top_k_requested": k,
            "hits_used": len(hits),
            "max_chunks_per_doc": 2,
            "hybrid_rerank": False,
        },
        "chroma2_status": status,
        "attribution_version": None,
    }


def cobalt_to_retrieval_context(packet: dict[str, Any]) -> dict[str, Any]:
    """Map cobalt_retrieval into RouterInputEnvelope retrieval_context.chunks."""
    chunks = []
    for hit in packet.get("hits") or []:
        chunks.append(
            {
                "source": "CHROMA-2",
                "doc_id": hit.get("doc_id"),
                "doc_name": hit.get("doc_name"),
                "excerpt": hit.get("excerpt"),
                "citation": hit.get("citation"),
                "concept_id": hit.get("concept_id"),
                "area_name": hit.get("area_name"),
                "family_name": hit.get("family_name"),
                "distance": hit.get("distance"),
            }
        )
    return {
        "chunks": chunks,
        "cobalt": {
            "version": packet.get("version"),
            "strategy": packet.get("strategy"),
            "chroma2_status": packet.get("chroma2_status"),
        },
    }
