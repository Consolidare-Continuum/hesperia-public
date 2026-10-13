# HESPERIA — LEVEL 4 Dict-A loader
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Load lexical_markers.yaml and build marker → concept_id lookup for session text attribution.
Текст сессии → токены → маркеры → концепты (Dict-B) → семья/область.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_DICT_A_DIR = Path(__file__).resolve().parent
_MARKERS_PATH = _DICT_A_DIR / "lexical_markers.yaml"
_COLLOQUIAL_PATH = _DICT_A_DIR / "dictA_colloquial.yaml"
_STOPWORDS_PATH = _DICT_A_DIR / "dictA_stopwords.yaml"

# Optional per-entry YAML field ``confidence_type``: scales weight at index build time (calibration).
CONFIDENCE_TYPE_MULTIPLIER: dict[str, float] = {
    "strong": 1.0,
    "weak": 0.3,
}


@lru_cache(maxsize=None)
def _load_yaml_cached(p: Path) -> Any:
    """Parse one YAML file once per process. Static ontology assets never change at runtime;
    lexical_markers.yaml alone is ~1.2MB/57k lines and costs ~15s to re-parse via PyYAML —
    every function below routes through this so the file is read once, not once per call.
    Callers must treat the returned object as read-only (it's the shared cached instance)."""
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _effective_marker_weight(entry: dict[str, Any], default_weight: float = 1.0) -> float:
    w = float(entry.get("weight", default_weight))
    ct = str(entry.get("confidence_type") or "strong").strip().lower()
    mult = CONFIDENCE_TYPE_MULTIPLIER.get(ct, 1.0)
    return w * mult


def load_lexical_markers(path: Path | str | None = None) -> dict[str, Any]:
    """
    Загрузить YAML с маркерами Dict-A.
    Возвращает сырой dict с ключами version, domain, entries, marker_count, concept_count.
    """
    p = Path(path) if path is not None else _MARKERS_PATH
    return _load_yaml_cached(p) or {}


def build_marker_to_concepts(path: Path | str | None = None) -> dict[str, list[tuple[str, float]]]:
    """
    Построить словарь: нормализованный маркер (lowercase) → список (concept_id, weight).
    Используется для сопоставления токенов текста с концептами.
    """
    data = load_lexical_markers(path)
    entries = data.get("entries") or []
    out: dict[str, list[tuple[str, float]]] = {}
    for e in entries:
        if not isinstance(e, dict):
            continue
        marker = e.get("marker")
        concept_id = e.get("concept_id")
        weight = _effective_marker_weight(e, 1.0)
        if not marker or not concept_id:
            continue
        key = str(marker).strip().lower()
        if key not in out:
            out[key] = []
        out[key].append((str(concept_id), weight))
    return out


def get_marker_stats(path: Path | str | None = None) -> dict[str, Any]:
    """Вернуть marker_count, concept_count и version из файла маркеров."""
    data = load_lexical_markers(path)
    return {
        "marker_count": data.get("marker_count", 0),
        "concept_count": data.get("concept_count", 0),
        "version": data.get("version"),
        "domain": data.get("domain"),
        "language": data.get("language"),
    }


def _entries_from_path(p: Path) -> list[dict]:
    """Load entries list from a YAML file (top-level 'entries' or list of marker dicts)."""
    data = _load_yaml_cached(p)
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return data.get("entries") or []


def build_phrase_marker_index(
    path: Path | str | None = None,
    phrase_file: Path | str | None = None,
) -> dict[str, dict[tuple[str, ...], list[tuple[str, float]]]]:
    """
    Построить индекс фразовых маркеров для O(1) lookup по кортежам токенов.

    Возвращает:
    {
      "phrase_length_2": {("сначала", "хороший"): [(concept_id, weight), ...], ...},
      "phrase_length_3": {("вы", "меня", "предали"): [(concept_id, weight), ...], ...},
    }
    Берёт записи из lexical_markers (где marker содержит пробел) и из phrase_file, если задан.
    """
    base = Path(path) if path is not None else _MARKERS_PATH
    entries = _entries_from_path(base)
    if phrase_file is not None:
        pf = Path(phrase_file)
        if pf.is_absolute():
            entries = entries + _entries_from_path(pf)
        else:
            phrase_path = (base.parent / pf) if base.exists() else (_DICT_A_DIR / pf)
            entries = entries + _entries_from_path(phrase_path)
    else:
        phrase_path = base.parent / "phrase_markers.yaml" if base.exists() else _DICT_A_DIR / "phrase_markers.yaml"
        if phrase_path.exists():
            entries = entries + _entries_from_path(phrase_path)

    out: dict[str, dict[tuple[str, ...], list[tuple[str, float]]]] = {
        "phrase_length_2": {},
        "phrase_length_3": {},
    }
    for e in entries:
        if not isinstance(e, dict):
            continue
        marker = e.get("marker")
        concept_id = e.get("concept_id")
        weight = _effective_marker_weight(e, 1.0)
        if not marker or not concept_id:
            continue
        marker = str(marker).strip().lower()
        if " " not in marker:
            continue
        words = tuple(marker.split())
        if len(words) == 2:
            key = "phrase_length_2"
            tkey = words
        elif len(words) == 3:
            key = "phrase_length_3"
            tkey = words
        else:
            continue
        if tkey not in out[key]:
            out[key][tkey] = []
        out[key][tkey].append((str(concept_id), weight))
    return out


def build_colloquial_marker_index(path: Path | str | None = None) -> dict[str, list[tuple[str, float]]]:
    """
    Построить индекс разговорных/аффективных маркеров (dictA_colloquial.yaml).
    Формат тот же: marker → [(concept_id, weight)]. Веса в файле обычно 1.2–1.3.
    """
    p = Path(path) if path is not None else _COLLOQUIAL_PATH
    entries = _entries_from_path(p)
    out: dict[str, list[tuple[str, float]]] = {}
    for e in entries:
        if not isinstance(e, dict):
            continue
        marker = e.get("marker")
        concept_id = e.get("concept_id")
        weight = _effective_marker_weight(e, 1.2)
        if not marker or not concept_id:
            continue
        key = str(marker).strip().lower()
        if key not in out:
            out[key] = []
        out[key].append((str(concept_id), weight))
    return out


def load_stopwords(path: Path | str | None = None) -> set[str]:
    """Загрузить clinical stopwords из dictA_stopwords.yaml (нормализованные, lowercase)."""
    p = Path(path) if path is not None else _STOPWORDS_PATH
    data = _load_yaml_cached(p) or {}
    words = data.get("stopwords") or []
    return {str(w).strip().lower() for w in words if w}
