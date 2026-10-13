# HESPERIA — LLM call structured JSONL trace (HSR-V7-D-25).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Append-only JSONL logging for router LLM boundary calls."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _log_path() -> Path | None:
    raw = os.environ.get("HESPERIA_LLM_CALL_LOG", "").strip()
    if not raw:
        return None
    return Path(raw)


def log_llm_call(
    *,
    input_hash: str,
    output_hash: str,
    provider: str,
    model: str,
    latency_ms: float,
    tokens: dict[str, int] | None = None,
    status: str = "ok",
    error: str | None = None,
    attempt: int = 1,
) -> None:
    """Append one JSONL record when HESPERIA_LLM_CALL_LOG is set."""
    path = _log_path()
    if path is None:
        return
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "input_hash": input_hash,
        "output_hash": output_hash,
        "provider": provider,
        "model": model,
        "latency_ms": round(latency_ms, 3),
        "status": status,
        "attempt": attempt,
    }
    if tokens:
        record["tokens"] = tokens
    if error:
        record["error"] = error
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


class LlmCallTimer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0
