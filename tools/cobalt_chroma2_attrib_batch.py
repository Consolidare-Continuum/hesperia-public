#!/usr/bin/env python3
"""COBALT G2 — batch Hesperia bounding on CHROMA-2 chunks (doc-level pilot).

Uses sealed engine /analyze path per document (first chunk + title) and writes
concept_id, area_name, family_name on all chunks for that doc_id.

Run from altitudine with Hesperia dev on PYTHONPATH:

  export HESPERIA_DEV_ROOT=/data/workspaces/hesperia
  export PYTHONPATH=$HESPERIA_DEV_ROOT
  python3 tools/cobalt_chroma2_attrib_batch.py --pilot --max-docs 30 --dry-run
  python3 tools/cobalt_chroma2_attrib_batch.py --pilot --max-docs 30 --apply

Ref: COBALT-04 · governance/SPEC-ETHAN-HESPERIA-COBALT-MODULE-BRANCH.md G2
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ATTRIB_VERSION = "cobalt-g2-0.1"

# fpf_bridge_v7_4 §4 — TFP tag pass seed terms. Seeded from the G3 pilot's own proven query set
# (COLOMBO-COBALT-05-G3-EVAL-2026-06-29.md: Kernberg TFP/borderline/transference/countertransference/
# Meltzer queries correctly hit clinical docs) — a starting heuristic, not a final classifier.
# Real scale-up (v7.4 §4) is Colombo's clinical judgment on which docs are genuinely TFP-grounding
# literature; this keyword match is deliberately conservative (defaults to "cobalt" when unsure)
# so it never mislabels general library content as TFP, only ever a starting candidate list for
# Colombo to confirm/expand.
TFP_SEED_TERMS: tuple[str, ...] = (
    "kernberg", "transference-focused", "tfp", "transference", "countertransference",
    "borderline personality", "meltzer", "psychodynamic", "object relations", "narcissistic transference",
    "керн берг", "кернберг", "перенос", "контрперенос", "пограничн", "объектных отношени",
)


def _compute_branch(text: str) -> str:
    """fpf_bridge_v7_4 §1/§4 — the `branch` facet (tfp/cobalt/core). Conservative keyword match
    against TFP_SEED_TERMS; defaults to "cobalt" (general library) when no term matches. Never
    computed from area_id/family_id alone — TFP's own family/area canon
    (specs/canon/area_structure_tfp.yaml, domain TFP_KERNBERG) is a separate grid from the
    production 288-family grid this attribution runs against, so the two don't cleanly map onto
    each other; text-level matching is the only signal available without Colombo's tagging pass.
    """
    lowered = (text or "").lower()
    return "tfp" if any(term in lowered for term in TFP_SEED_TERMS) else "cobalt"
CHROMA_HOST = os.environ.get("COBALT_CHROMA_HOST", "chroma-2.prichindel.local")
CHROMA_PORT = int(os.environ.get("COBALT_CHROMA_PORT", "8002"))
COLLECTION = "documents"
SCAN_BATCH = 500


def _repo_root() -> Path:
    return Path(os.environ.get("HESPERIA_DEV_ROOT", Path(__file__).resolve().parents[1]))


def _ensure_hesperia_path() -> None:
    root = str(_repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def _chroma_collection():
    import chromadb

    return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT).get_collection(COLLECTION)


def _scan_doc_index(coll, max_chunks: int) -> dict[str, dict[str, Any]]:
    """Map doc_id -> representative chunk row (first seen)."""
    docs: dict[str, dict[str, Any]] = {}
    offset = 0
    scanned = 0
    while scanned < max_chunks and len(docs) < 5000:
        part = coll.get(
            limit=min(SCAN_BATCH, max_chunks - scanned),
            offset=offset,
            include=["documents", "metadatas"],
        )
        ids = part.get("ids") or []
        if not ids:
            break
        for cid, doc, meta in zip(
            ids,
            part.get("documents") or [],
            part.get("metadatas") or [],
        ):
            meta = meta or {}
            doc_id = str(meta.get("doc_id") or "")
            if not doc_id or doc_id in docs:
                continue
            if meta.get("concept_id") and meta.get("area_name"):
                continue
            docs[doc_id] = {
                "chunk_id": cid,
                "text": (doc or "")[:2500],
                "meta": meta,
            }
        scanned += len(ids)
        offset += len(ids)
        if len(ids) < SCAN_BATCH:
            break
    return docs


def _compose_doc_text(meta: dict[str, Any], chunk_text: str) -> str:
    title = str(meta.get("title") or meta.get("doc_name") or "")
    creator = str(meta.get("creator") or "")
    parts = [p for p in (title, creator, chunk_text) if p]
    return " ".join(parts)[:4000]


def _attrib_from_engine(text: str) -> dict[str, str]:
    from runtime.services.engine_analyze_contract import run_engine_analyze

    eng = run_engine_analyze(text)
    area_id = str(eng.get("dominant_area_id") or "")
    family_id = str(eng.get("dominant_family_id") or "")
    concept_id = str(eng.get("dominant_concept_id") or "")
    return {
        "concept_id": concept_id[:128],
        "area_id": area_id[:32],
        "area_name": area_id[:64],
        "family_name": family_id[:64],
        "global_id": family_id[:64],
        "branch": _compute_branch(text),
    }


def _chunks_for_doc(coll, doc_id: str, limit: int = 5000) -> list[tuple[str, dict[str, Any]]]:
    part = coll.get(
        where={"doc_id": doc_id},
        limit=limit,
        include=["metadatas"],
    )
    out: list[tuple[str, dict[str, Any]]] = []
    for cid, meta in zip(part.get("ids") or [], part.get("metadatas") or []):
        out.append((cid, meta or {}))
    return out


def run_batch(*, max_docs: int, scan_chunks: int, apply: bool, out_path: Path) -> dict[str, Any]:
    coll = _chroma_collection()
    index = _scan_doc_index(coll, scan_chunks)
    doc_ids = list(index.keys())[:max_docs]
    report: dict[str, Any] = {
        "attrib_version": ATTRIB_VERSION,
        "ts": int(time.time()),
        "max_docs": max_docs,
        "candidates": len(index),
        "processed": [],
        "errors": [],
        "apply": apply,
    }
    updated_chunks = 0
    for doc_id in doc_ids:
        row = index[doc_id]
        meta = row["meta"]
        try:
            text = _compose_doc_text(meta, row["text"])
            fields = _attrib_from_engine(text)
            fields["attribution_version"] = ATTRIB_VERSION
            fields["attribution_ts"] = int(time.time())
            chunk_rows = _chunks_for_doc(coll, doc_id)
            report["processed"].append(
                {
                    "doc_id": doc_id,
                    "doc_name": meta.get("doc_name"),
                    "chunks": len(chunk_rows),
                    **fields,
                }
            )
            if apply:
                for cid, old_meta in chunk_rows:
                    new_meta = {**old_meta, **fields}
                    coll.update(ids=[cid], metadatas=[new_meta])
                    updated_chunks += 1
        except Exception as exc:
            report["errors"].append({"doc_id": doc_id, "error": str(exc)})
    report["updated_chunks"] = updated_chunks
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    _ensure_hesperia_path()
    ap = argparse.ArgumentParser(description="COBALT G2 CHROMA-2 attribution batch")
    ap.add_argument("--pilot", action="store_true", help="Pilot mode (default limits)")
    ap.add_argument("--max-docs", type=int, default=30)
    ap.add_argument("--scan-chunks", type=int, default=8000)
    ap.add_argument("--apply", action="store_true", help="Write metadata to CHROMA-2")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("operational/cobalt/g2_attrib_batch_report.json"),
    )
    args = ap.parse_args()
    if args.pilot:
        args.max_docs = min(args.max_docs, 50)
        args.scan_chunks = min(args.scan_chunks, 10000)
    report = run_batch(
        max_docs=args.max_docs,
        scan_chunks=args.scan_chunks,
        apply=args.apply,
        out_path=args.out,
    )
    print(
        json.dumps(
            {
                "docs": len(report["processed"]),
                "errors": len(report["errors"]),
                "updated_chunks": report.get("updated_chunks", 0),
                "out": str(args.out),
            }
        )
    )
    return 0 if report["processed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
