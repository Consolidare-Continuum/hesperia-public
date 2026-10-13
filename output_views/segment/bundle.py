"""T02 — Build session_inspector_v1 from engine artifact or minimal dict."""

from __future__ import annotations

import copy
from typing import Any

from .constants import SESSION_INSPECTOR_SCHEMA_VERSION


def build_session_inspector_v1(artifact: dict[str, Any] | None) -> dict[str, Any]:
    """
    Normalize arbitrary engine / E2E JSON into a minimal session bundle.

    Expected optional top-level keys from callers: meta, iterations (list).
    Unknown keys are preserved under meta['extra'] when present.
    """
    src = copy.deepcopy(artifact) if artifact else {}
    meta = dict(src.get("meta") or {})
    extra = {k: v for k, v in src.items() if k not in ("meta", "iterations")}
    if extra:
        meta.setdefault("extra", {}).update(extra)

    iterations = src.get("iterations")
    if iterations is None and src.get("iteration") is not None:
        iterations = [src["iteration"]]
    if not isinstance(iterations, list):
        iterations = []

    return {
        "schema_version": SESSION_INSPECTOR_SCHEMA_VERSION,
        "meta": meta,
        "iterations": iterations,
    }
