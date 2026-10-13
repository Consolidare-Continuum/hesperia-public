# HESPERIA — frozen anchor_map_v1 registry (METRIC-17/19, IPoV-01 reconcile).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ANCHOR_MAP_PATH = _REPO_ROOT / "assets" / "schemas" / "anchor_map_v1.json"

FROZEN_ANCHOR_MAP_ID = "anchor_map_v1"


@lru_cache(maxsize=1)
def load_anchor_map_v1() -> dict[str, Any]:
    with _ANCHOR_MAP_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("anchor_map_id") != FROZEN_ANCHOR_MAP_ID:
        raise ValueError(f"anchor_map_v1.json anchor_map_id mismatch: {data.get('anchor_map_id')!r}")
    if data.get("status") != "FROZEN":
        raise ValueError("anchor_map_v1.json is not FROZEN")
    return data


def frozen_anchor_map_id() -> str:
    return str(load_anchor_map_v1()["anchor_map_id"])
