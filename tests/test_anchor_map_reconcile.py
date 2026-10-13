"""METRIC-19 — anchor_map_v1 frozen registry matches IPoV-01 rule."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]


def test_anchor_map_v1_frozen_registry() -> None:
    path = _REPO / "assets" / "schemas" / "anchor_map_v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["anchor_map_id"] == "anchor_map_v1"
    assert data["status"] == "FROZEN"
    assert data["families_gcs_250"] == 48
    assert data["families_gcs_251"] == 240
    assert data["families_gcs_250"] + data["families_gcs_251"] == 288


def test_hesperia_metric_emit_uses_frozen_anchor_map_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from runtime.services.anchor_map_registry import load_anchor_map_v1
    from runtime.services.hesperia_metric_emit import build_hesperia_metric_block

    load_anchor_map_v1.cache_clear()
    block = build_hesperia_metric_block()
    assert block["anchor_map_id"] == "anchor_map_v1"
    assert block["gcs_surface"]["anchor_map_id"] == "anchor_map_v1"
    assert block["ipow_volume"]["anchor_map_id"] == "anchor_map_v1"
