# HESPERIA — Regex phrase patterns for TFP (LEVEL 15 dicts enhancement)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Match phrase_patterns.yaml regexes on session text; weight 1.5 for transference indicators.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_DICT_A_DIR = Path(__file__).resolve().parent.parent / "ontology" / "dictA"
_PATTERNS_PATH = _DICT_A_DIR / "phrase_patterns.yaml"

_compiled: list[tuple[re.Pattern[str], str, float]] | None = None


def _load_and_compile(path: Path | str | None = None) -> list[tuple[re.Pattern[str], str, float]]:
    global _compiled
    if _compiled is not None and path is None:
        return _compiled
    import yaml
    p = Path(path) if path is not None else _PATTERNS_PATH
    if not p.exists():
        _compiled = [] if path is None else []
        return _compiled
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        data = data.get("entries") or data.get("patterns") or []
    out: list[tuple[re.Pattern[str], str, float]] = []
    for e in data:
        if not isinstance(e, dict):
            continue
        pattern_str = e.get("pattern")
        concept_id = e.get("concept_id")
        weight = float(e.get("weight", 1.5))
        if not pattern_str or not concept_id:
            continue
        try:
            out.append((re.compile(str(pattern_str), re.IGNORECASE), str(concept_id), weight))
        except re.error:
            continue
    if path is None:
        _compiled = out
    return out


def load_phrase_patterns(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load raw phrase patterns from YAML (pattern, concept_id, weight)."""
    import yaml
    p = Path(path) if path is not None else _PATTERNS_PATH
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    if isinstance(data, list):
        return [e for e in data if isinstance(e, dict) and e.get("pattern") and e.get("concept_id")]
    return []


def detect_phrase_patterns(
    text: str,
    path: Path | str | None = None,
) -> list[tuple[str, float]]:
    """
    Run regex patterns from phrase_patterns.yaml on text. Returns list of (concept_id, weight).
    Each pattern fires at most once per text (first match).
    """
    if not text or not isinstance(text, str):
        return []
    compiled = _load_and_compile(path)
    out: list[tuple[str, float]] = []
    seen: set[str] = set()
    text_lower = text.lower()
    for pattern, concept_id, weight in compiled:
        if concept_id in seen:
            continue
        if pattern.search(text_lower):
            out.append((concept_id, weight))
            seen.add(concept_id)
    return out
