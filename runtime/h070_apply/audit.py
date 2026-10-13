# H070 apply audit JSONL trace.
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

DEFAULT_AUDIT = Path("/tmp/hesperia-h070-apply-audit.jsonl")


def append_apply_audit(entry: dict[str, Any], path: Path | None = None) -> None:
    path = path or DEFAULT_AUDIT
    path.parent.mkdir(parents=True, exist_ok=True)
    row = dict(entry)
    row.setdefault("ts", int(time.time()))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
