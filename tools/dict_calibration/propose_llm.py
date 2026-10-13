# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Task 3 — Map normalized lexicals to concept proposals (reuse existing ids when possible)."""

from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any, Literal

from .env_defaults import normalize_domain
from .openai_json import chat_json

Domain = Literal["tfp", "core"]

# --- TFP (legacy clinical) ---
SYSTEM_TFP = """You map lexical phrases (Russian and/or English clinical / TFP discourse) to a controlled concept vocabulary.
Prefer reusing existing concept_id values exactly when meaning matches.
Limit new concepts: only when no existing id fits; use dotted ids like tfp.domain.name
If the input list is non-empty you MUST return at least one concept object with non-empty from_lexical drawn ONLY from that list.
Output strict JSON only."""

USER_TEMPLATE_TFP = """Existing concepts (reuse these ids when possible):
{catalog}

Normalized lexical items:
{items}

Return JSON: {{"concepts": [
  {{"concept_id": str, "labels": [str], "from_lexical": [str], "confidence": float}}
]}}
Each from_lexical entry must be copied from the input phrase list. Merge synonyms under one concept.
Cap total concepts at {max_concepts}."""

# --- core/default (syzif book prose) — Class A; DEFAULT for all propose callers ---
SYSTEM_CORE = """You map lexical phrases from published book prose (English primary; other languages when present)
to the core/default controlled concept vocabulary (AREA_FAMILY_MAP families).
Prefer reusing existing concept_id values exactly when meaning matches (ids look like core.<area>.<family-slug>).
Do not invent TFP/session-discourse framing or tfp.* ids.
Limit new concepts: only when no existing id fits; new ids must use the core.<area>.<slug> shape.
If the input list is non-empty you MUST return at least one concept object with non-empty from_lexical drawn ONLY from that list.
Output strict JSON only."""

USER_TEMPLATE_CORE = """Existing concepts in the candidate's area/family neighborhood (reuse these ids when possible):
{catalog}

Lexical items from the corpus:
{items}

Return JSON: {{"concepts": [
  {{"concept_id": str, "labels": [str], "from_lexical": [str], "confidence": float}}
]}}
Each from_lexical entry must be copied from the input phrase list. Merge synonyms under one concept.
Cap total concepts at {max_concepts}."""

# Default aliases = CORE (Class A). Pass domain="tfp" only for Class B TFP runs.
SYSTEM = SYSTEM_CORE
USER_TEMPLATE = USER_TEMPLATE_CORE


def _sanitize_phrase_for_json(value: str) -> str:
    # Remove NULs and replace invalid UTF-8 code points deterministically.
    s = str(value).replace("\x00", "")
    return s.encode("utf-8", errors="replace").decode("utf-8")


def _is_request_json_body_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "could not parse the json body of your request" in msg or "invalid_request_error" in msg


def _is_non_json_or_truncated_reply(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "openai returned non-json or truncated json" in msg


def _templates_for(domain: Domain) -> tuple[str, str]:
    normalized = normalize_domain(domain)
    if normalized == "core":
        return SYSTEM_CORE, USER_TEMPLATE_CORE
    return SYSTEM_TFP, USER_TEMPLATE_TFP


def _row_area_family_keys(row: dict[str, Any]) -> tuple[str, str]:
    area = str(row.get("area_name") or row.get("area_id") or (row.get("area_ids") or [""])[0] or "")
    fam = str(row.get("family_name") or row.get("preferred_label") or row.get("family_id") or (row.get("family_ids") or [""])[0] or "")
    return area.lower(), fam.lower()


def _catalog_rows(
    dict_b_rows: list[dict[str, Any]],
    *,
    limit: int = 400,
    area_name: str | None = None,
    family_name: str | None = None,
    domain: Domain = "core",
) -> str:
    """
    Format catalog lines for the prompt.

    core domain: prefer area/family neighborhood. A 288-row seed fits without truncation
    when neighborhood is the full area (24 families) or the full seed when no hint.
    """
    rows = list(dict_b_rows)
    if domain == "core" and (area_name or family_name):
        an = (area_name or "").lower()
        fn = (family_name or "").lower()
        scoped = []
        for row in rows:
            ra, rf = _row_area_family_keys(row)
            if an and ra == an:
                scoped.append(row)
            elif fn and (rf == fn or fn in rf or rf in fn):
                scoped.append(row)
        if scoped:
            rows = scoped
        # 288 seed: no need to truncate if small
        if len(rows) <= 288:
            limit = max(limit, len(rows))
    lines = []
    for row in rows[:limit]:
        cid = row.get("concept_id")
        lab = row.get("preferred_label") or row.get("definition", "")[:80]
        area = row.get("area_name") or row.get("area_id") or ""
        fam = row.get("family_name") or ""
        if area or fam:
            lines.append(f"- {cid}: {lab} [{area}/{fam}]")
        else:
            lines.append(f"- {cid}: {lab}")
    return "\n".join(lines)


def call_propose_chunk(
    chunk: list[str],
    catalog: str,
    *,
    max_concepts: int,
    domain: Domain = "core",
) -> list[dict[str, Any]]:
    """One OpenAI call for ``chunk`` phrases; returns raw ``concepts`` list (may be empty)."""
    system, user_tmpl = _templates_for(domain)
    chunk = [_sanitize_phrase_for_json(x) for x in chunk]
    user = user_tmpl.format(
        catalog=catalog,
        # Keep payload JSON-safe even with malformed corpus unicode.
        items=_json.dumps(chunk, ensure_ascii=True),
        max_concepts=max_concepts,
    )
    try:
        raw = chat_json(system=system, user=user)
    except Exception as e:
        if len(chunk) > 1 and (_is_request_json_body_error(e) or _is_non_json_or_truncated_reply(e)):
            # Recover by splitting problematic payload; clearance checkpoints still progress.
            mid = len(chunk) // 2
            left = call_propose_chunk(chunk[:mid], catalog, max_concepts=max_concepts, domain=domain)
            right = call_propose_chunk(chunk[mid:], catalog, max_concepts=max_concepts, domain=domain)
            return [*left, *right]
        raise
    arr = raw.get("concepts") if isinstance(raw, dict) else None
    if not isinstance(arr, list):
        raise ValueError("call_propose_chunk: expected {concepts: [...]}")
    if len(arr) == 0 and chunk:
        raw = chat_json(
            system=system,
            user=user
            + "\n\nYour previous reply had an empty concepts array. Regroup the SAME items; minimum 1 concept.",
            temperature=0.25,
        )
        arr = raw.get("concepts") if isinstance(raw, dict) else None
        if not isinstance(arr, list):
            raise ValueError("call_propose_chunk: retry expected {concepts: [...]}")
    return arr


def merge_concept_rows_into_state(
    arr: list[Any],
    merged: list[dict[str, Any]],
    seen: set[str],
) -> None:
    """Append deduped concept dicts from API ``arr`` into ``merged`` / ``seen`` (same rules as full propose)."""
    for c in arr:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("concept_id", "")).strip()
        if not cid:
            continue
        fl = [str(x) for x in (c.get("from_lexical") or []) if str(x).strip()]
        key = cid + "|" + "|".join(sorted(fl))
        if key in seen:
            continue
        seen.add(key)
        merged.append(
            {
                "concept_id": cid,
                "labels": [str(x) for x in (c.get("labels") or [])],
                "from_lexical": fl,
                "confidence": float(c.get("confidence") or 0.5),
            }
        )


def write_proposals_raw_checkpoint(
    path: Path | str,
    *,
    batch_index: int,
    chunk: list[str],
    concepts: list[dict[str, Any]],
    accepted: list[dict[str, Any]] | None = None,
) -> None:
    """Persist full batch output (accepts + rejects context) — note-all discipline."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    accepted = accepted or []
    accepted_ids = {c.get("concept_id") for c in accepted}
    rec = {
        "batch_index": batch_index,
        "chunk": chunk,
        "concepts": concepts,
        "accepted_concept_ids": sorted(x for x in accepted_ids if x),
        "note": "raw LLM batch; includes proposals that may fail later anchor min_score",
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(_json.dumps(rec, ensure_ascii=False) + "\n")


def propose_concepts(
    normalized_rows: list[dict[str, Any]],
    dict_b_rows: list[dict[str, Any]],
    *,
    max_concepts: int = 80,
    batch_size: int = 40,
    catalog_limit: int = 400,
    domain: Domain = "core",
    area_name: str | None = None,
    family_name: str | None = None,
    raw_checkpoint_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    catalog = _catalog_rows(
        dict_b_rows,
        limit=catalog_limit if domain == "tfp" else max(catalog_limit, len(dict_b_rows)),
        area_name=area_name,
        family_name=family_name,
        domain=domain,
    )
    phrases = [str(r.get("normalized") or r.get("text", "")).strip() for r in normalized_rows]
    phrases = [p for p in phrases if p]
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    for i in range(0, len(phrases), batch_size):
        chunk = phrases[i : i + batch_size]
        arr = call_propose_chunk(chunk, catalog, max_concepts=max_concepts, domain=domain)
        before = len(merged)
        merge_concept_rows_into_state(arr, merged, seen)
        if raw_checkpoint_path is not None:
            write_proposals_raw_checkpoint(
                raw_checkpoint_path,
                batch_index=i // batch_size,
                chunk=chunk,
                concepts=list(arr) if isinstance(arr, list) else [],
                accepted=merged[before:],
            )
    return merged
