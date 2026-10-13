# HESPERIA — Multi-word Marker Detection (2–5 n-grams)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Обнаружение клинических маркеров-фраз (2–5 слов): мне кажется вы, как будто вы,
вы специально, вам всё равно. Отдельный слой от токеновых маркеров.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hesperia.nlp.session_parser import build_ngram_tuples

_DICT_A_DIR = Path(__file__).resolve().parent.parent / "ontology" / "dictA"
_PHRASE_MARKERS_PATH = _DICT_A_DIR / "phrase_markers.yaml"
_LEXICAL_PATH = _DICT_A_DIR / "lexical_markers.yaml"


def _load_ngram_entries(min_n: int = 2, max_n: int = 5) -> list[dict]:
    """Загрузить из phrase_markers и lexical_markers записи, где marker содержит пробелы (2–5 слов)."""
    import yaml
    entries = []
    for p in (_PHRASE_MARKERS_PATH, _LEXICAL_PATH):
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for e in (data.get("entries") or data if isinstance(data, list) else []):
            if not isinstance(e, dict):
                continue
            marker = (e.get("marker") or "").strip()
            if " " in marker:
                wc = len(marker.split())
                if min_n <= wc <= max_n:
                    entries.append(e)
    return entries


def build_ngram_marker_index(
    min_n: int = 2,
    max_n: int = 5,
) -> dict[int, dict[tuple[str, ...], list[tuple[str, float]]]]:
    """
    Индекс n-грамм (длины min_n..max_n) → [(concept_id, weight)].
    Ключ уровня — длина n; значение — словарь tuple(tokens) → список (concept_id, weight).
    """
    entries = _load_ngram_entries(min_n=min_n, max_n=max_n)
    out: dict[int, dict[tuple[str, ...], list[tuple[str, float]]]] = {}
    for n in range(min_n, max_n + 1):
        out[n] = {}
    for e in entries:
        marker = (e.get("marker") or "").strip().lower()
        concept_id = e.get("concept_id")
        weight = float(e.get("weight", 1.0))
        if not marker or not concept_id:
            continue
        words = tuple(marker.split())
        if len(words) < min_n or len(words) > max_n:
            continue
        n = len(words)
        if n not in out:
            out[n] = {}
        out[n].setdefault(words, []).append((str(concept_id), weight))
    return out


def detect_ngram_markers(
    tokens: list[str],
    index: dict[int, dict[tuple[str, ...], list[tuple[str, float]]]] | None = None,
    min_n: int = 2,
    max_n: int = 5,
) -> list[tuple[str, float]]:
    """
    Найти все совпадения n-грамм (длины min_n..max_n) в tokens с индексом.
    Возвращает список (concept_id, weight). Концепт не дублируется (первое совпадение).
    """
    if not tokens or not index:
        index = build_ngram_marker_index(min_n=min_n, max_n=max_n)
    seen: set[str] = set()
    result: list[tuple[str, float]] = []
    for n in range(min_n, max_n + 1):
        idx = index.get(n) or {}
        for tup in build_ngram_tuples(tokens, n):
            hits = idx.get(tup)
            if not hits:
                continue
            for cid, w in hits:
                if cid not in seen:
                    seen.add(cid)
                    result.append((cid, w))
    return result
