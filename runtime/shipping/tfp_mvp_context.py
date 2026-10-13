# HESPERIA — TFP MVP context packet (API + agent shared).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Build allowlisted ``context_packet`` for TFP Class B instructor path.

Uses only keys accepted by shipping ``InterpretBody`` (FPF-HSR-11):
``retrieval``, ``coherence_hints``, ``corpus_snapshot_id``, ``observability``.

Same builder for HTTP clients and in-process agents.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_CORPUS_SNAPSHOT_ID = "tfp_mvp_inspector_exports_v1"
_MAX_SNIPPET_CHARS = 1200
_MAX_DOCS = 4


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _byte_budget() -> int:
    return int(os.environ.get("HESPERIA_MAX_CONTEXT_PACKET_BYTES", "20000") or "20000")


def _trim_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Keep context_packet under HESPERIA_MAX_CONTEXT_PACKET_BYTES (task 60)."""
    import json

    budget = _byte_budget()
    raw = json.dumps(packet, ensure_ascii=False)
    if len(raw.encode("utf-8")) <= budget:
        return packet
    out = dict(packet)
    retrieval = dict(out.get("retrieval") or {})
    docs = list(retrieval.get("documents") or [])
    while docs and len(json.dumps(out, ensure_ascii=False).encode("utf-8")) > budget:
        docs.pop()
        retrieval["documents"] = docs
        retrieval["doc_count"] = len(docs)
        retrieval["trimmed"] = True
        out["retrieval"] = retrieval
    return out


def _structure_map_hints(repo: Path) -> dict[str, Any]:
    canon = repo / "assets" / "specs" / "canon"
    area = canon / "area_structure_tfp.yaml"
    families = canon / "families_structure_tfp.yaml"
    return {
        "pack": "tfp",
        "area_math_grain": int(os.environ.get("HESPERIA_AREA_MATH_GRAIN") or "10"),
        "area_structure_path": str(area.relative_to(repo)) if area.is_file() else None,
        "families_structure_path": str(families.relative_to(repo)) if families.is_file() else None,
        "area_structure_present": area.is_file(),
        "families_structure_present": families.is_file(),
        "dict_mode": "full_tfp_stack",
        "note": "TFP structure map + full dict stack MVP; geometry lock remains 12/288",
    }


def _inspector_export_docs(repo: Path) -> list[dict[str, str]]:
    root = repo / "hesperia" / "modules" / "tfp" / "data" / "tfp_v1" / "inspector_exports"
    if not root.is_dir():
        return []
    docs: list[dict[str, str]] = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in (".md", ".json", ".jsonl", ".txt"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        docs.append(
            {
                "id": path.name,
                "path": str(path.relative_to(repo)),
                "snippet": text[:_MAX_SNIPPET_CHARS],
            }
        )
        if len(docs) >= _MAX_DOCS:
            break
    return docs


def build_tfp_mvp_context_packet(
    *,
    repo_root: Path | None = None,
    query_text: str | None = None,
) -> dict[str, Any]:
    """Return allowlisted context_packet for TFP instructor (API + agent).

    Prefer CHROMA-2 ``documents`` (profile tfp_ru). Fallback: inspector_exports
    only when CHROMA-2 unreachable or empty (task 53–61).
    """
    repo = repo_root or _repo_root()
    retrieval: dict[str, Any]
    snapshot = _CORPUS_SNAPSHOT_ID
    q = (query_text or "").strip() or "TFP поле перенос рамки"
    try:
        from runtime.shipping.tfp_chroma2_retrieve import (
            corpus_snapshot_id_for_retrieval,
            retrieve_tfp_library,
        )

        retrieval = retrieve_tfp_library(q)
        if retrieval.get("status") == "ok" and int(retrieval.get("doc_count") or 0) > 0:
            snapshot = corpus_snapshot_id_for_retrieval(retrieval)
        else:
            # Fallback inspector_exports when CHROMA-2 unreachable/empty.
            docs = _inspector_export_docs(repo)
            retrieval = {
                "source": "tfp_v1/inspector_exports",
                "status": "fallback_inspector" if docs else (retrieval.get("status") or "empty"),
                "doc_count": len(docs),
                "documents": docs,
                "chroma_prior": {
                    "status": retrieval.get("status"),
                    "error": retrieval.get("error"),
                    "chroma_url": retrieval.get("chroma_url"),
                },
                "corpus_home": "chroma-2_colombo_library",
            }
            snapshot = _CORPUS_SNAPSHOT_ID if docs else "chroma2_tfp_ru_unavailable"
    except Exception as exc:  # noqa: BLE001
        docs = _inspector_export_docs(repo)
        retrieval = {
            "source": "tfp_v1/inspector_exports",
            "status": "fallback_inspector" if docs else "empty",
            "doc_count": len(docs),
            "documents": docs,
            "error": f"{type(exc).__name__}: {exc}",
            "corpus_home": "chroma-2_colombo_library",
        }
    packet = {
        "corpus_snapshot_id": snapshot,
        "retrieval": retrieval,
        "coherence_hints": {
            "structure_map": _structure_map_hints(repo),
            "instructor": "analyze_then_interpret",
            "lane": "tfp_class_b",
            "corpus_home": "chroma-2_colombo_library",
            "disk_sessions_empty_not_missing_corpus": True,
        },
        "observability": {
            "analyze_profile": "tfp",
            "corpus_snapshot_id": snapshot,
            "mvp_label": "dict_stack+structure+chroma2_retrieve",
            "sessions_corpus": "empty",
            "corpus_home": "chroma-2_colombo_library",
        },
    }
    return _trim_packet(packet)


def merge_tfp_mvp_context(
    context_packet: dict[str, Any] | None,
    *,
    repo_root: Path | None = None,
    force: bool = False,
    query_text: str | None = None,
) -> dict[str, Any]:
    """Merge MVP pack into an existing packet without clobbering caller retrieval."""
    base = dict(context_packet or {})
    if not force and base.get("corpus_snapshot_id") and isinstance(base.get("retrieval"), dict):
        # Caller already supplied retrieval — keep it, still attach structure hints.
        mvp = build_tfp_mvp_context_packet(repo_root=repo_root, query_text=query_text)
        out = {**mvp, **base}
        out["retrieval"] = base["retrieval"]
        if "coherence_hints" in base and isinstance(base["coherence_hints"], dict):
            merged_hints = dict(mvp.get("coherence_hints") or {})
            merged_hints.update(base["coherence_hints"])
            out["coherence_hints"] = merged_hints
        return _trim_packet(out)
    mvp = build_tfp_mvp_context_packet(repo_root=repo_root, query_text=query_text)
    out = {**mvp, **base}
    if "retrieval" in base and isinstance(base["retrieval"], dict):
        out["retrieval"] = base["retrieval"]
    if "coherence_hints" in base and isinstance(base["coherence_hints"], dict):
        merged_hints = dict(mvp.get("coherence_hints") or {})
        merged_hints.update(base["coherence_hints"])
        out["coherence_hints"] = merged_hints
    return _trim_packet(out)
