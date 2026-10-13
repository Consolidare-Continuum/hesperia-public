"""MySQL ledger for Hesperia 0.6.3 teach runs (H063-36..40)."""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Mapping

FORBIDDEN_PROSE_KEYS = frozenset({"justification", "message", "explanation"})


def _target_type(action: str) -> str:
    if action in ("add_edge", "remove_edge", "update_edge_weight"):
        return "edge"
    if action == "update_cd_field":
        return "cd_field"
    if action == "add_concept":
        return "concept"
    return "bridge"


def persist_teach_run(
    envelope: Mapping[str, Any],
    teacher_request: Mapping[str, Any],
    teacher_response: Mapping[str, Any] | None,
    *,
    status: str = "stored",
    irc_channel: str | None = None,
) -> str:
    """Persist run to MySQL when MYSQL_HESPERIA_DSN is set; else no-op return run_id."""
    run_id = str(envelope.get("run_id", uuid.uuid4()))
    dsn = os.environ.get("MYSQL_HESPERIA_DSN", "").strip()
    if not dsn:
        return run_id

    import pymysql

    conn = pymysql.connect(**_parse_dsn(dsn))
    try:
        with conn.cursor() as cur:
            engine = envelope.get("engine") or {}
            cur.execute(
                """
                INSERT INTO hesperia_teacher_run
                (run_id, correlation_id, lang, input_text_ru, input_kind,
                 engine_envelope, teacher_request, teacher_response, irc_channel, status,
                 hesperia_git_sha, tersagor_git_sha, openai_model)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    run_id,
                    envelope.get("correlation_id"),
                    envelope.get("lang", "ru"),
                    (envelope.get("input") or {}).get("text_ru", ""),
                    (envelope.get("input") or {}).get("kind", "tfp_scientific_statement"),
                    json.dumps(envelope, ensure_ascii=False),
                    json.dumps(teacher_request, ensure_ascii=False),
                    json.dumps(teacher_response, ensure_ascii=False) if teacher_response else None,
                    irc_channel,
                    status,
                    engine.get("hesperia_ref"),
                    engine.get("integration_host_ref") or engine.get("tersagor_ref"),
                    os.environ.get("HESPERIA_KSI_TEACHER_MODEL"),
                ),
            )
            _persist_snapshots(cur, run_id, envelope, teacher_response)
        conn.commit()
    finally:
        conn.close()
    return run_id


def _persist_snapshots(
    cur: Any, run_id: str, envelope: Mapping[str, Any], teacher_response: Mapping[str, Any] | None
) -> None:
    ksi = envelope.get("ksi") or {}
    for concept_row in (envelope.get("engine") or {}).get("corpus_activations") or []:
        if not isinstance(concept_row, dict):
            continue
        cur.execute(
            """
            INSERT INTO hesperia_activation_snapshot
            (run_id, concept_id, label_ru, observed, expected, residual, incident_type)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                run_id,
                concept_row.get("concept_id"),
                None,
                concept_row.get("observed", 0),
                concept_row.get("expected"),
                None,
                None,
            ),
        )
    phi = ksi.get("phi_trace") or {}
    if isinstance(phi, dict):
        for edge_key, row in phi.items():
            if not isinstance(row, dict) or "->" not in edge_key:
                continue
            src, tgt = edge_key.split("->", 1)
            cur.execute(
                """
                INSERT INTO hesperia_edge_snapshot
                (run_id, source_concept_id, target_concept_id, relation_type, W_e, R_e, phi_sat)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    run_id,
                    src,
                    tgt,
                    row.get("type", "activates"),
                    row.get("W_e", 0),
                    row.get("R_e"),
                    row.get("phi_sat"),
                ),
            )
    if teacher_response:
        for seq, prop in enumerate(teacher_response.get("proposals") or []):
            if not isinstance(prop, dict):
                continue
            if FORBIDDEN_PROSE_KEYS & set(prop.keys()):
                continue
            pid = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO hesperia_proposal
                (proposal_id, run_id, seq, action, target_type, payload, confidence, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'pending')
                """,
                (
                    pid,
                    run_id,
                    seq,
                    prop.get("action"),
                    _target_type(str(prop.get("action", ""))),
                    json.dumps(prop, ensure_ascii=False),
                    prop.get("confidence"),
                ),
            )


def _parse_dsn(dsn: str) -> dict[str, Any]:
    from urllib.parse import urlparse

    u = urlparse(dsn)
    return {
        "host": u.hostname or "127.0.0.1",
        "port": u.port or 3306,
        "user": u.username,
        "password": u.password,
        "database": (u.path or "/hesperia").lstrip("/"),
        "charset": "utf8mb4",
    }
