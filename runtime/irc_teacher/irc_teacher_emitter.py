"""IRC trace emitter for Hesperia 0.6.3 teach runs (H063-27..28)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

CHANNEL_DEFAULT = "#hesperia-teacher"
CHUNK_SIZE = 3800


def _audit_path() -> Path:
    base = Path(os.environ.get("HESPERIA_TEACHER_AUDIT_DIR", os.path.expanduser("~/ergo/logs/hesperia-teacher")))
    base.mkdir(parents=True, exist_ok=True)
    return base / "irc-trace.jsonl"


def _emit_line(msg_type: str, payload: Mapping[str, Any], channel: str) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "channel": channel,
        "type": msg_type,
        "payload": payload,
    }
    line = json.dumps(record, ensure_ascii=False) + "\n"
    _audit_path().open("a", encoding="utf-8").write(line)


def _chunk_json(msg_type: str, data: Mapping[str, Any], correlation_id: str, channel: str) -> None:
    raw = json.dumps(data, ensure_ascii=False)
    if len(raw) <= CHUNK_SIZE:
        _emit_line(msg_type, dict(data), channel)
        return
    parts = [raw[i : i + CHUNK_SIZE] for i in range(0, len(raw), CHUNK_SIZE)]
    for idx, part in enumerate(parts):
        _emit_line(
            msg_type,
            {"correlation_id": correlation_id, "chunk": idx, "chunks": len(parts), "body": part},
            channel,
        )


def emit_run_start(correlation_id: str, run_id: str, *, channel: str | None = None) -> None:
    ch = channel or CHANNEL_DEFAULT
    _emit_line("RUN_START", {"correlation_id": correlation_id, "run_id": run_id, "lang": "ru"}, ch)


def emit_engine_envelope(envelope: Mapping[str, Any], *, channel: str | None = None) -> None:
    ch = channel or CHANNEL_DEFAULT
    _chunk_json("ENGINE_ENVELOPE", envelope, str(envelope.get("correlation_id", "")), ch)


def emit_teacher_request(req: Mapping[str, Any], correlation_id: str, *, channel: str | None = None) -> None:
    ch = channel or CHANNEL_DEFAULT
    _chunk_json("TEACHER_REQUEST", req, correlation_id, ch)


def emit_teacher_response(resp: Mapping[str, Any], correlation_id: str, *, channel: str | None = None) -> None:
    ch = channel or CHANNEL_DEFAULT
    _chunk_json("TEACHER_RESPONSE", resp, correlation_id, ch)


def emit_reweight_preview(preview: list[Mapping[str, Any]], correlation_id: str, *, channel: str | None = None) -> None:
    ch = channel or CHANNEL_DEFAULT
    _emit_line("REWEIGHT_PREVIEW", {"correlation_id": correlation_id, "preview": preview}, ch)


def emit_run_done(correlation_id: str, run_id: str, status: str, *, channel: str | None = None) -> None:
    ch = channel or CHANNEL_DEFAULT
    _emit_line("RUN_DONE", {"correlation_id": correlation_id, "run_id": run_id, "status": status}, ch)
