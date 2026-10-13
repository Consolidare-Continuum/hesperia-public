# HESPERIA — Family embedding loader (two-scale geometry)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Load spec/family_embedding_tfp.yaml: local family lattice per area (center/inner_ring/middle_ring/outer_ring)
and cross-area bridges. Used for propagation and geometric interpretation.
Do not flatten 240 families onto the sphere — family index remains nested under area.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Repo root: .../hesperia/sphere/topology/this_file → parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]
# Legacy layout (often absent); canonical file lives under specs/canon/ (see AGENTS.md spec symlink).
_LEGACY_SPEC = Path(__file__).resolve().parents[2] / "spec" / "family_embedding_tfp.yaml"
_CANON_EMBEDDING = _REPO_ROOT / "assets" / "specs" / "canon" / "family_embedding_tfp.yaml"
_SYMLINK_SPEC = _REPO_ROOT / "spec" / "family_embedding_tfp.yaml"

# Zone keys in embedding YAML per area
ZONE_KEYS = ("center", "inner_ring", "middle_ring", "outer_ring")
# Expected counts per area: 1 + 6 + 8 + 9 = 24
ZONE_COUNTS = {"center": 1, "inner_ring": 6, "middle_ring": 8, "outer_ring": 9}


def _embedding_path_candidates() -> list[Path]:
    return [_SYMLINK_SPEC, _CANON_EMBEDDING, _LEGACY_SPEC]


def load_family_embedding_tfp(path: str | Path | None = None) -> dict[str, Any]:
    """
    Загрузить family_embedding_tfp.yaml.
    Возвращает dict с ключами: version, domain, A2, A3, A4, A10 (и др. области), bridges, zones.
    Каждая область: center (list[str]), inner_ring, middle_ring, outer_ring (списки локальных F1..F24).
    bridges: list of {from, to, type}.

    Default search: ``<repo>/spec/family_embedding_tfp.yaml`` (symlink), then
    ``specs/canon/family_embedding_tfp.yaml``, then legacy ``hesperia/spec/...``.
    """
    candidates = [Path(path)] if path is not None else _embedding_path_candidates()
    for p in candidates:
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            return data
    return _empty_embedding()


def _empty_embedding() -> dict[str, Any]:
    return {
        "version": 0,
        "domain": "",
        "bridges": [],
        "zones": {},
    }


def get_area_zones(embedding: dict[str, Any], area_id: str) -> dict[str, list[str]]:
    """
    Для области вернуть зоны: center, inner_ring, middle_ring, outer_ring.
    Каждое значение — список локальных id семей (F1..F24).
    """
    area_data = embedding.get(area_id)
    if not isinstance(area_data, dict):
        return {z: [] for z in ZONE_KEYS}
    out: dict[str, list[str]] = {}
    for z in ZONE_KEYS:
        val = area_data.get(z)
        if isinstance(val, list):
            out[z] = [str(x) for x in val]
        else:
            out[z] = []
    return out


def get_bridges(embedding: dict[str, Any]) -> list[dict[str, str]]:
    """Список мостов: [{from, to, type}, ...]. from/to — составной id, например A2_F5."""
    bridges = embedding.get("bridges")
    if not isinstance(bridges, list):
        return []
    out: list[dict[str, str]] = []
    for b in bridges:
        if not isinstance(b, dict):
            continue
        fr = b.get("from")
        to = b.get("to")
        t = b.get("type", "activates")
        if fr and to:
            out.append({"from": str(fr), "to": str(to), "type": str(t)})
    return out


def get_composite_family_id(area_id: str, local_family: str) -> str:
    """
    Составной id семьи: area_id + "_F" + локальный номер. Пример: A3, F6 → A3_F6.
    local_family может быть "F6" или "6"; нормализуем к формату A3_F6.
    """
    s = str(local_family).strip().upper()
    if s.startswith("F"):
        return f"{area_id}_{s}"
    return f"{area_id}_F{s}"
