# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from pathlib import Path

from runtime.pipeline.run_tfp_file_pipeline import load_sessions


def test_load_sessions_plain_text(tmp_path: Path) -> None:
    p = tmp_path / "note.md"
    p.write_text("hello world", encoding="utf-8")
    assert load_sessions(p) == [("note", "hello world")]


def test_load_sessions_json_sessions(tmp_path: Path) -> None:
    p = tmp_path / "s.json"
    p.write_text(
        json.dumps(
            {
                "sessions": [
                    {"session_id": "a", "text": "one"},
                    {"session_id": "b", "text": "two"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert load_sessions(p) == [("a", "one"), ("b", "two")]
