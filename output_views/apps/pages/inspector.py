"""Session Inspector — load fixture bundles and resolve iteration / sentence selection."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from django.conf import settings
from django.http import Http404

_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,120}$")


def load_inspector_fixture(session_id: str) -> dict[str, Any]:
    """T13 — read-only JSON from tests/fixtures (MVP); no path traversal."""
    if not _SESSION_ID_RE.match(session_id):
        raise Http404("invalid session id")
    path = Path(settings.BASE_DIR) / "tests" / "fixtures" / f"{session_id}.json"
    if not path.is_file():
        raise Http404("bundle not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise Http404("bundle unreadable") from e


def sorted_iterations(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    iters = bundle.get("iterations") or []
    if not isinstance(iters, list):
        return []
    return sorted(iters, key=lambda x: int(x.get("order", 0)))


def resolve_iteration(bundle: dict[str, Any], order_query: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Pick iteration by `order` field; default first."""
    iters = sorted_iterations(bundle)
    if not iters:
        raise Http404("no iterations in bundle")
    if order_query is None or order_query == "":
        return iters[0], iters
    try:
        want = int(order_query)
    except ValueError:
        return iters[0], iters
    for it in iters:
        if int(it.get("order", -1)) == want:
            return it, iters
    return iters[0], iters


def iteration_label(it: dict[str, Any]) -> str:
    sentences = it.get("sentences") or []
    if isinstance(sentences, list) and sentences:
        t = str(sentences[0].get("text", "")).strip()
        if len(t) > 48:
            t = t[:45] + "…"
        return t or f"Iteration {it.get('order', 0)}"
    return f"Iteration {it.get('order', 0)}"


def sourced_text_lines(it: dict[str, Any]) -> list[dict[str, Any]]:
    """Pane A — prefer sentences[]; else single iteration.text if present."""
    sents = it.get("sentences")
    if isinstance(sents, list) and sents:
        return sorted(sents, key=lambda x: int(x.get("order", 0)))
    raw = it.get("text")
    if isinstance(raw, str) and raw.strip():
        return [{"id": "s0", "text": raw, "order": 0}]
    return []
