# H070 replay benchmark runner — fixed TFP statements, documented flags.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "h070" / "fixtures" / "replay_tfp_statements.json"


def load_replay_benchmarks(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or DEFAULT_FIXTURE
    data = json.loads(p.read_text(encoding="utf-8"))
    items = data.get("statements") or []
    if not isinstance(items, list):
        raise ValueError("replay fixture: statements must be a list")
    return items


def run_replay_benchmarks(
    *,
    fixture_path: Path | None = None,
    engine_flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """G4 stub: each statement must be non-empty; flags echoed for audit."""
    statements = load_replay_benchmarks(fixture_path)
    flags = engine_flags or {"engine_sha": "fixture", "replay_mode": "h070-offline"}
    results = []
    for row in statements:
        text = str(row.get("text") or "").strip()
        results.append(
            {
                "id": row.get("id"),
                "text_len": len(text),
                "ok": bool(text),
                "tags": row.get("tags") or [],
            }
        )
    ok_count = sum(1 for r in results if r["ok"])
    return {
        "flags": flags,
        "total": len(results),
        "ok_count": ok_count,
        "pass": ok_count == len(results) and len(results) >= 10,
        "results": results,
    }
