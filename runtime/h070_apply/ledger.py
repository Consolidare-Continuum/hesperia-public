# H070 apply ledger — MySQL applied=1 stub via JSONL until prod wiring.
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

DEFAULT_LEDGER = Path("/tmp/hesperia-h070-apply-ledger.jsonl")


def record_applied(
    *,
    proposal_id: str,
    canonical_hash: str,
    approval_id: str,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    """G9 ledger row — `applied=1` after G1–G8 pass."""
    if not proposal_id or not canonical_hash or not approval_id:
        raise ValueError("proposal_id, canonical_hash, approval_id required")
    row = {
        "proposal_id": proposal_id,
        "canonical_hash": canonical_hash,
        "approval_id": approval_id,
        "applied": 1,
        "ts": int(time.time()),
    }
    path = ledger_path or DEFAULT_LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row
