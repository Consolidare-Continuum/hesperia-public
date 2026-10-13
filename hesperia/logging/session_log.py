# HESPERIA — Activation Logging (JSONL)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Для исследований: raw text, tokens, lemmas, markers, concept activations,
graph nodes, graph edges, metrics. Формат: JSONL (одна строка — один JSON-объект).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO


def log_session_record(
    path: str | Path,
    record: dict[str, Any],
    append: bool = True,
) -> None:
    """
    Записать одну запись сессии в JSONL-файл.
    record: raw_text, tokens, lemmas, markers, concepts, families, areas,
            graph_nodes, graph_edges, metrics, session_id, ontology_version, ...
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and p.exists() else "w"
    with open(p, mode, encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _serialize(obj: Any) -> Any:
    """Свести к JSON-serializable типам."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(x) for x in obj]
    return str(obj)


class SessionLogWriter:
    """
    Контекстный писатель JSONL: накапливает поля записи и пишет одну строку при close/commit.
    """

    def __init__(self, path: str | Path, append: bool = True):
        self.path = Path(path)
        self.append = append
        self._record: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._record[key] = _serialize(value)

    def write(self) -> None:
        if not self._record:
            return
        log_session_record(self.path, self._record, append=self.append)
        self._record = {}

    def __enter__(self) -> "SessionLogWriter":
        return self

    def __exit__(self, *args: Any) -> None:
        self.write()
