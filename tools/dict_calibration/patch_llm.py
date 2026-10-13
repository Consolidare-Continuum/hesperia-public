# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Task 8 — LLM proposes dict patches from error surface (applied only after review)."""

from __future__ import annotations

import json as _json
from typing import Any

from .openai_json import chat_json

SYSTEM = """You are assisting dictionary calibration for a deterministic psychodynamics engine.
Propose minimal JSON patches; do not invent engine topology; prefer linking to existing concept ids.
Output strict JSON."""

USER = """Errors:
{errors}

Existing link sample (max 40):
{links}

Return JSON patch object:
{{
  "add_lexical": [{{"lexical": str, "concept_id": str, "priority": float}}],
  "merge_concepts": [{{"from_id": str, "into_id": str}}],
  "split_concepts": [{{"concept_id": str, "new_lexical_routes": [{{"lexical": str, "concept_id": str}}]}}],
  "adjust_priorities": [{{"lexical": str, "priority": float}}],
  "notes": str
}}"""


def propose_patch(
    errors: list[dict[str, Any]],
    links_sample: list[dict[str, Any]],
    *,
    max_errors: int = 80,
    max_links: int = 40,
) -> dict[str, Any]:
    return chat_json(
        system=SYSTEM,
        user=USER.format(
            errors=_json.dumps(errors[:max_errors], ensure_ascii=False),
            links=_json.dumps(links_sample[:max_links], ensure_ascii=False),
        ),
        temperature=0.2,
    )


def apply_patch_to_links(
    links: list[dict[str, Any]],
    patch: dict[str, Any],
) -> list[dict[str, Any]]:
    """Deterministically merge patch.add_lexical and adjust_priorities into links."""
    by_lex = {str(x["lexical"]): dict(x) for x in links if x.get("lexical")}
    for row in patch.get("add_lexical") or []:
        if not isinstance(row, dict):
            continue
        lx = str(row.get("lexical", "")).strip()
        cid = str(row.get("concept_id", "")).strip()
        if not lx or not cid:
            continue
        pr = float(row.get("priority", 0.85))
        by_lex[lx] = {
            "lexical": lx,
            "concept_id": cid,
            "match_type": "pattern",
            "priority": round(pr, 4),
        }
    for row in patch.get("adjust_priorities") or []:
        if not isinstance(row, dict):
            continue
        lx = str(row.get("lexical", "")).strip()
        if lx in by_lex:
            by_lex[lx]["priority"] = round(float(row.get("priority", 0.5)), 4)
    return sorted(by_lex.values(), key=lambda r: (-float(r.get("priority", 0)), r["lexical"]))
