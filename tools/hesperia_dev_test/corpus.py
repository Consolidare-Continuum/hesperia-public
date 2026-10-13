# HESPERIA — hesperia-dev-test synthetic corpus. Copyright © 2026 igareosh.com.
"""Semantics-free token corpus: bare Latin letters, digits, booleans, diacritics, index-shaped
strings. No real dictionary words. Used to check core structural/logic consistency without
attributing product meaning to any token.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

_LETTERS = "abcdefghijklmnopqrstuvwxyz"
_CASEFOLD_PROBES = "abcxyz"
_DIGITS = [str(i) for i in range(10)]
_NUMERIC = ["42", "999", "007", "1000000"]
_BOOLS = ["true", "false", "t", "f"]
# Romanian diacritics — chosen because TOKEN_RE (core/lexical/normalization.py) has no
# diacritic-folding step; these are expected to fragment the input, not to fail cleanly.
_DIACRITIC_CHARS = "ăâîșț"
_DIACRITIC_WORDS = ("mână", "inteligență", "român", "început", "știință")
_INDICES = ["idx0", "idx1", "n1", "a1b2", "x0y0z0"]

# Colombo Bench-0 design (2026-07-26): lane classification. bench0_latin is the GOLD lane —
# structural/math equality only, pinned in gold/bench0_v0_1.json. Everything else is a later
# lane; diacritic is KNOWN_BEHAVIOR (silent tokenizer truncation — see ETHAN-HDT-01 findings),
# never a Bench-0 pass/fail criterion.
LANE_BENCH0_GOLD = "bench0_latin"
LANE_KNOWN_BEHAVIOR = frozenset({"diacritic"})


@dataclass(frozen=True)
class CorpusEntry:
    id: str
    token: str
    cls: str


def _entry(token: str, cls: str) -> CorpusEntry:
    eid = hashlib.sha1(f"{cls}:{token}".encode("utf-8")).hexdigest()[:10]
    return CorpusEntry(id=eid, token=token, cls=cls)


def letters() -> list[CorpusEntry]:
    return [_entry(c, "letter") for c in _LETTERS]


def casefold_pairs() -> list[CorpusEntry]:
    return [_entry(c.upper(), "casefold_pair") for c in _CASEFOLD_PROBES]


def digits() -> list[CorpusEntry]:
    return [_entry(d, "digit") for d in _DIGITS] + [_entry(n, "numeric") for n in _NUMERIC]


def booleans() -> list[CorpusEntry]:
    return [_entry(b, "bool") for b in _BOOLS]


def diacritics() -> list[CorpusEntry]:
    return [_entry(c, "diacritic") for c in _DIACRITIC_CHARS] + [
        _entry(w, "diacritic") for w in _DIACRITIC_WORDS
    ]


def indices() -> list[CorpusEntry]:
    return [_entry(i, "index") for i in _INDICES]


def bench0_latin() -> list[CorpusEntry]:
    """The GOLD lane (Colombo Bench-0, 2026-07-26): bare a-z + casefold twins only. This is the
    default corpus for `pytest -m dev_test` and the CLI fast path — everything else is soak."""
    return letters() + casefold_pairs()


def full_corpus() -> list[CorpusEntry]:
    out: list[CorpusEntry] = []
    out += letters()
    out += casefold_pairs()
    out += digits()
    out += booleans()
    out += diacritics()
    out += indices()
    return out
