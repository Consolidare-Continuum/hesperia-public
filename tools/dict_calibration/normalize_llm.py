# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Task 2 — LLM collapse of noisy surface strings to stable lexical forms."""

from __future__ import annotations

import json as _json
import os
from typing import Any

from openai import BadRequestError

from .openai_json import chat_json

SYSTEM = """You normalize clinical / psychodynamic surface text to compact lexical phrases.
Rules: aggressive removal of fillers; preserve psychological meaning; lower-case output;
no diagnosis labels; output strict JSON only."""

USER_TEMPLATE = """Given items (each has row_id, pattern_type, text, freq), return JSON object with key "items" array.
Each output element: {{"row_id": str, "source_text": str, "normalized": str, "variants": [str, ...]}}
row_id must match the input row_id. source_text should echo the input text (or its surface form).
Merge paraphrases to one normalized form; variants lists surface alternates (max 8).
Input:
{payload}
"""


def _text_cap_from_env() -> int | None:
    v = os.environ.get("HESPERIA_CALIB_NORMALIZE_INPUT_TEXT_CAP", "").strip()
    if v.isdigit():
        return max(1, int(v))
    return None


def _cap_text(s: Any, cap: int | None) -> str:
    t = str(s or "")
    if cap is not None and cap > 0 and len(t) > cap:
        return t[:cap]
    return t


def _payload_for_chunk(
    chunk: list[dict[str, Any]],
    *,
    text_cap: int | None,
) -> list[dict[str, Any]]:
    return [
        {
            "row_id": str(i),
            "pattern_type": r.get("pattern_type"),
            "text": _cap_text(r.get("text"), text_cap),
            "freq": r.get("freq"),
        }
        for i, r in enumerate(chunk)
    ]


def _merge_items_into_chunk(chunk: list[dict[str, Any]], items: list[Any]) -> list[dict[str, Any]]:
    by_rid: dict[str, dict[str, Any]] = {}
    by_src: dict[str, dict[str, Any]] = {}
    for x in items:
        if not isinstance(x, dict):
            continue
        rid = str(x.get("row_id", "")).strip()
        if rid:
            by_rid[rid] = x
        st = str(x.get("source_text", ""))
        if st:
            by_src[st] = x
    out: list[dict[str, Any]] = []
    for i, r in enumerate(chunk):
        full_text = str(r.get("text", ""))
        hit = by_rid.get(str(i)) or by_src.get(full_text) or {}
        norm = str(hit.get("normalized") or full_text).strip()
        vars_ = hit.get("variants") if isinstance(hit.get("variants"), list) else []
        vars_clean = [str(v).strip() for v in vars_ if str(v).strip()][:12]
        rec = dict(r)
        rec["normalized"] = norm
        rec["variants"] = vars_clean
        out.append(rec)
    return out


def _normalize_chunk_one_pass(
    chunk: list[dict[str, Any]],
    *,
    text_cap: int | None,
) -> list[dict[str, Any]]:
    if not chunk:
        return []
    payload = _payload_for_chunk(chunk, text_cap=text_cap)
    raw = chat_json(
        system=SYSTEM,
        user=USER_TEMPLATE.format(payload=_json.dumps(payload, ensure_ascii=False)),
    )
    items = raw.get("items") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        raise ValueError("normalize_batch: expected {items: [...]}")
    return _merge_items_into_chunk(chunk, items)


def _normalize_single_row_degrading_caps(chunk: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assert len(chunk) == 1
    last_err: BadRequestError | None = None
    for cap in (24000, 12000, 6000, 3000, 1500, 800, 400):
        try:
            return _normalize_chunk_one_pass(chunk, text_cap=cap)
        except BadRequestError as e:
            last_err = e
            continue
    if last_err is not None:
        raise last_err
    raise RuntimeError("normalize: single-row retries exhausted")


def _normalize_chunk_with_retry(chunk: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not chunk:
        return []
    env_cap = _text_cap_from_env()
    try:
        return _normalize_chunk_one_pass(chunk, text_cap=env_cap)
    except BadRequestError:
        if len(chunk) > 1:
            mid = max(1, len(chunk) // 2)
            return _normalize_chunk_with_retry(chunk[:mid]) + _normalize_chunk_with_retry(chunk[mid:])
        return _normalize_single_row_degrading_caps(chunk)


def normalize_batch(rows: list[dict[str, Any]], *, batch_size: int = 24) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        out.extend(_normalize_chunk_with_retry(chunk))
    return out
