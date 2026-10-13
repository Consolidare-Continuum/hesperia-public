"""H063-19/32: IRC-visible Teacher application run orchestrator (Hesperia product repo)."""
from __future__ import annotations

import os
import uuid
from typing import Any

from runtime.irc_teacher.analyze_adapter import HybridRetrieveInput, retrieve
from runtime.irc_teacher.engine_run_envelope import (
    build_engine_run_envelope,
    build_teacher_request_from_envelope,
)
from runtime.irc_teacher.flags import irc_teacher_enabled, ksi_enabled
from runtime.irc_teacher.irc_teacher_emitter import (
    emit_engine_envelope,
    emit_reweight_preview,
    emit_run_done,
    emit_run_start,
    emit_teacher_request,
    emit_teacher_response,
)
from runtime.irc_teacher.mysql_ledger import persist_teach_run
from runtime.irc_teacher.teacher_v063 import call_openai_teacher_v063, compute_reweight_preview


def run_irc_teacher_path(
    text_ru: str,
    *,
    correlation_id: str | None = None,
    channel: str | None = None,
) -> dict[str, Any]:
    if not irc_teacher_enabled():
        raise RuntimeError(
            "IRC teacher path disabled (set HESPERIA_IRC_TEACHER=1 or TERSAGOR_HESPERIA_IRC_TEACHER=1)"
        )

    cid = correlation_id or f"cid-{uuid.uuid4().hex[:12]}"
    inp = HybridRetrieveInput(query=text_ru, mode="hybrid")
    if ksi_enabled():
        os.environ.setdefault("HESPERIA_KSI_ENABLED", "1")

    hybrid_out = retrieve(inp)
    envelope = build_engine_run_envelope(
        text_ru=text_ru,
        correlation_id=cid,
        hybrid_output=hybrid_out,
    )
    run_id = envelope["run_id"]
    emit_run_start(cid, run_id, channel=channel)
    emit_engine_envelope(envelope, channel=channel)

    teacher_request = build_teacher_request_from_envelope(envelope)
    emit_teacher_request(teacher_request, cid, channel=channel)

    teacher_response = call_openai_teacher_v063(teacher_request)
    emit_teacher_response(teacher_response, cid, channel=channel)

    preview = compute_reweight_preview(list(teacher_response.get("proposals") or []))
    emit_reweight_preview(preview, cid, channel=channel)

    persist_teach_run(envelope, teacher_request, teacher_response, irc_channel=channel)
    emit_run_done(cid, run_id, "stored", channel=channel)

    return {
        "correlation_id": cid,
        "run_id": run_id,
        "envelope": envelope,
        "teacher_request": teacher_request,
        "teacher_response": teacher_response,
        "reweight_preview": preview,
    }
