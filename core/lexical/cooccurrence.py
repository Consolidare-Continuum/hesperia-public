# HESPERIA — RAD. Deterministic token co-occurrence (Ethan PO-22).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

_TOKEN = re.compile(r"[a-z0-9]+")


def token_pair_counts(tokens: Iterable[str], window: int = 4) -> dict[tuple[str, str], int]:
    """Ordered pairs (t_i, t_j) with j in (i+1..i+window), i < j index."""
    tlist = [str(x).casefold() for x in tokens if str(x).strip()]
    counts: Counter[tuple[str, str]] = Counter()
    for i, a in enumerate(tlist):
        for j in range(i + 1, min(i + 1 + window, len(tlist))):
            b = tlist[j]
            if a < b:
                counts[(a, b)] += 1
            elif b < a:
                counts[(b, a)] += 1
            else:
                counts[(a, b)] += 1
    return dict(counts)


def pair_counts_from_canonical(canonical_text: str, window: int = 4) -> dict[tuple[str, str], int]:
    return token_pair_counts(_TOKEN.findall(canonical_text), window=window)
