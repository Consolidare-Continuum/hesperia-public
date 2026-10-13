# HESPERIA — Russian morphological normalization (LEVEL 15 dicts enhancement)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Lemmatize Russian tokens via pymorphy2 for improved Dict-A marker lookup.
Examples: ненавижу → ненавидеть, бесился → беситься, боялась → бояться.
"""

from __future__ import annotations

_PYMORPHY_AVAILABLE: bool | None = None
_MORPH: object = None


def _get_morph():
    """Lazy init pymorphy2 MorphAnalyzer."""
    global _PYMORPHY_AVAILABLE, _MORPH
    if _PYMORPHY_AVAILABLE is False:
        return None
    if _MORPH is not None:
        return _MORPH
    try:
        import pymorphy2
        _MORPH = pymorphy2.MorphAnalyzer()
        _PYMORPHY_AVAILABLE = True
        return _MORPH
    except Exception:
        _PYMORPHY_AVAILABLE = False
        return None


def lemmatize_tokens(tokens: list[str]) -> list[str]:
    """
    Return list of lemmas for each token. Uses pymorphy2 for Russian;
    non-Russian tokens and failures return the original token (lowercased).
    """
    if not tokens:
        return []
    morph = _get_morph()
    if morph is None:
        return [t.strip().lower() if isinstance(t, str) else str(t) for t in tokens]
    result: list[str] = []
    for t in tokens:
        if not isinstance(t, str) or not t.strip():
            continue
        s = t.strip().lower()
        parsed = morph.parse(s)
        if parsed:
            result.append(parsed[0].normal_form)
        else:
            result.append(s)
    return result


def is_lemmatizer_available() -> bool:
    """Return True if pymorphy2 is installed and usable."""
    return _get_morph() is not None
