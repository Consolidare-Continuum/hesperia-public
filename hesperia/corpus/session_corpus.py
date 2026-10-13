# HESPERIA — Corpus Management
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Corpus loader, indexing, metadata: session_id, therapist_id, patient_id,
session_number, date.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SessionMetadata:
    session_id: str
    therapist_id: str = ""
    patient_id: str = ""
    session_number: int = 0
    date: str = ""
    path: str = ""
    extra: dict[str, Any] | None = None


def load_corpus_manifest(path: Path | str) -> list[dict[str, Any]]:
    """
    Загрузить манифест корпуса (YAML/JSON): список сессий с метаданными.
    Ожидаемые поля: session_id, therapist_id, patient_id, session_number, date, path.
    """
    p = Path(path)
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        if p.suffix.lower() in (".json",):
            import json
            data = json.load(f)
        else:
            data = yaml.safe_load(f) or {}
    sessions = data.get("sessions", data if isinstance(data, list) else [])
    return [s for s in sessions if isinstance(s, dict)]


def load_session(
    base_dir: Path | str,
    entry: dict[str, Any],
    text_key: str = "path",
) -> tuple[str, SessionMetadata]:
    """
    Загрузить текст сессии по записи из манифеста.
    entry[text_key] — путь к файлу относительно base_dir или абсолютный.
    Возвращает (text, SessionMetadata).
    """
    base = Path(base_dir)
    path_val = entry.get(text_key, "") or entry.get("path", "")
    if not path_val:
        return "", SessionMetadata(session_id=entry.get("session_id", ""))
    p = Path(path_val)
    if not p.is_absolute():
        p = base / p
    text = ""
    if p.exists():
        text = p.read_text(encoding="utf-8")
    meta = SessionMetadata(
        session_id=str(entry.get("session_id", "")),
        therapist_id=str(entry.get("therapist_id", "")),
        patient_id=str(entry.get("patient_id", "")),
        session_number=int(entry.get("session_number", 0)),
        date=str(entry.get("date", "")),
        path=str(p),
        extra={k: v for k, v in entry.items() if k not in ("session_id", "therapist_id", "patient_id", "session_number", "date", "path")},
    )
    return text, meta


def list_sessions(manifest_path: Path | str) -> list[SessionMetadata]:
    """Список метаданных сессий из манифеста."""
    entries = load_corpus_manifest(manifest_path)
    return [
        SessionMetadata(
            session_id=e.get("session_id", ""),
            therapist_id=e.get("therapist_id", ""),
            patient_id=e.get("patient_id", ""),
            session_number=int(e.get("session_number", 0)),
            date=str(e.get("date", "")),
            path=str(e.get("path", "")),
        )
        for e in entries
    ]
