# HESPERIA — Negation Detection
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Negation scope detection: «я не злюсь», «я не ненавижу вас» не должны
активировать ложную агрессию. Помечаем токены/фразы в области отрицания.
"""

from __future__ import annotations

import re
from typing import Any

# Отрицание (рус. / англ.) — начало scope до конца предложения или до следующего пунктуатора/союза
NEGATION_HEAD = re.compile(
    r"\b(не|ни|нет|никогда|ничего|никто|нисколько|ничуть|вовсе не|отнюдь не|don't|doesn't|didn't|isn't|aren't|wasn't|weren't|cannot|can't|won't|wouldn't|never|nothing|nobody|no one)\b",
    re.IGNORECASE,
)
# Конец scope: союз, точка, запятая (приближённо — до следующего «и», «а», «но», «,», «.»)
SCOPE_END = re.compile(r"\s+(и|а|но|или|зато|даже)\s+", re.IGNORECASE)


def find_negation_scopes(text: str) -> list[tuple[int, int]]:
    """
    Найти интервалы (start, end) символов в text, попадающие в scope отрицания.
    Каждый scope — от начала совпадения NEGATION_HEAD до конца предложения или до SCOPE_END.
    """
    if not text or not isinstance(text, str):
        return []
    scopes: list[tuple[int, int]] = []
    for m in NEGATION_HEAD.finditer(text):
        start = m.start()
        rest = text[m.end() :]
        end_match = SCOPE_END.search(rest)
        if end_match:
            scope_end = m.end() + end_match.start()
        else:
            scope_end = len(text)
        scopes.append((start, scope_end))
    return scopes


def token_in_negation_scope(
    token_start: int,
    token_end: int,
    scopes: list[tuple[int, int]],
) -> bool:
    """Проверить, пересекается ли span токена [token_start, token_end) с любым negation scope."""
    for s, e in scopes:
        if token_start < e and token_end > s:
            return True
    return False


def filter_negated_markers(
    tokens: list[str],
    token_offsets: list[tuple[int, int]] | None,
    text: str,
    markers: list[tuple[str, float]],
    concept_to_token_indices: dict[str, list[int]] | None = None,
) -> list[tuple[str, float]]:
    """
    Исключить из markers те концепты, которые были активированы токенами в области отрицания.
    concept_to_token_indices: concept_id -> list of token indices that triggered it (если есть).
    Иначе используем text и token_offsets: для каждого маркера нужно знать, какой токен его дал —
    здесь упрощение: если токен по offset попадает в scope, все маркеры от этого токена отбрасываем.
    Упрощённый вариант: передаём markers и список индексов токенов, попавших в negation;
    возвращаем markers без концептов, активированных этими индексами.
    """
    scopes = find_negation_scopes(text)
    if not scopes or not token_offsets:
        return list(markers)
    negated_indices: set[int] = set()
    for i, (s, e) in enumerate(token_offsets):
        if token_in_negation_scope(s, e, scopes):
            negated_indices.add(i)
    if not negated_indices and concept_to_token_indices is None:
        return list(markers)
    # Без concept_to_token_indices не можем сопоставить marker с токеном — возвращаем как есть
    if concept_to_token_indices is None:
        return list(markers)
    out = []
    for cid, w in markers:
        indices = concept_to_token_indices.get(cid, [])
        if not any(idx in negated_indices for idx in indices):
            out.append((cid, w))
    return out


def is_negated_span(text: str, start: int, end: int) -> bool:
    """Проверить, попадает ли span [start, end) в любой negation scope в text."""
    scopes = find_negation_scopes(text)
    return token_in_negation_scope(start, end, scopes)


def get_negated_token_indices(text: str, tokens: list[str]) -> set[int]:
    """
    Вернуть множество индексов токенов, попадающих в scope отрицания.
    Токены ищутся в text по порядку (первое вхождение после предыдущего).
    """
    if not text or not tokens:
        return set()
    scopes = find_negation_scopes(text)
    if not scopes:
        return set()
    text_lower = text.lower()
    pos = 0
    negated: set[int] = set()
    for i, tok in enumerate(tokens):
        if not tok:
            continue
        idx = text_lower.find(tok.lower(), pos)
        if idx == -1:
            pos = 0
            idx = text_lower.find(tok.lower(), pos)
        if idx >= 0:
            if token_in_negation_scope(idx, idx + len(tok), scopes):
                negated.add(i)
            pos = idx + len(tok)
    return negated
