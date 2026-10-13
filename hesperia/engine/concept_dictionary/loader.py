# HESPERIA — Concept Dictionary loader (jsonl). Copyright © 2026 igareosh.com.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hesperia.engine.concept_dictionary.validator import validate_cd_row, CDValidationError


def load_cd_registry(path: Path) -> dict[str, dict[str, Any]]:
    """Load concept_id -> row dict. Last wins. ``*`` must exist after merge (or injected default)."""
    if not path.is_file():
        raise FileNotFoundError(f"CD registry missing: {path}")
    reg: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise CDValidationError(f"line {line_no}: invalid JSON: {e}") from e
            validate_cd_row(row, line_no=line_no)
            cid = str(row["concept_id"])
            reg[cid] = row
    if "*" not in reg:
        reg["*"] = _default_star_row()
    return dict(sorted(reg.items(), key=lambda x: x[0]))


def _default_star_row() -> dict[str, Any]:
    return {
        "concept_id": "*",
        "type": "state",
        "activation": {
            "base_weight": 1.0,
            "cap": 2.0,
            "saturation_k": 1.0,
            "threshold": 0.0,
        },
        "constraints": {"requires": [], "excludes": [], "co_occurs": []},
        "effects": {"amplifies": {}, "inhibits": {}},
        "structure": {"primary_area": "", "secondary_areas": [], "family_bias": []},
    }
