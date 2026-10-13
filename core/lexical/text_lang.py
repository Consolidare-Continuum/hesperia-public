# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.
"""Heuristic document language labels for lexical calibration (RU vs EN, no external API)."""

from __future__ import annotations


def _count_scripts(text: str) -> tuple[int, int, int]:
    """Return (cyrillic_letters, latin_letters, other)."""
    cy = la = 0
    for ch in text:
        o = ord(ch)
        if 0x0400 <= o <= 0x04FF or 0x0500 <= o <= 0x052F:
            cy += 1
        elif ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            la += 1
    return cy, la, len(text) - cy - la


def heuristic_document_language(text: str) -> str:
    """
    Return a coarse label: ``ru``, ``en``, ``mixed``, or ``und``.

    Used for comparing input text to ``dict_c.language`` metadata and for reports.
    """
    if not (text or "").strip():
        return "und"
    cy, la, _ = _count_scripts(text)
    letters = cy + la
    if letters == 0:
        return "und"
    rcy, rla = cy / letters, la / letters
    if rcy >= 0.35 and rla >= 0.25:
        return "mixed"
    if rcy > rla and rcy >= 0.15:
        return "ru"
    if rla > rcy and rla >= 0.15:
        return "en"
    if rcy > 0:
        return "ru"
    if rla > 0:
        return "en"
    return "und"


# Backwards-compatible name for Grace directive wording
match_language = heuristic_document_language


def retag_language_field_for_phrase(normalized_form: str) -> str:
    """
    Per-row Dict C ``language`` correction from script only (no API).

    Rules: Cyrillic-only → ``ru``; Latin-only → ``en``; both or neither letters → ``mixed``.
    """
    nf = (normalized_form or "").strip()
    if not nf:
        return "mixed"
    cy, la, _ = _count_scripts(nf)
    if cy > 0 and la == 0:
        return "ru"
    if la > 0 and cy == 0:
        return "en"
    return "mixed"
