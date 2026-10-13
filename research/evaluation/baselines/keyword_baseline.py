# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Crude contradiction proxy: opposing term co-occurrence in sliding windows."""

from __future__ import annotations

import re
from typing import Any

_POS = frozenset(
    {"growth", "freedom", "success", "expansion", "support", "benefit", "gain", "win", "progress"}
)
_NEG = frozenset(
    {"cut", "ban", "crisis", "block", "fail", "loss", "risk", "threat", "deny", "oppose", "against"}
)


def run_keyword_baseline(text: str, window: int = 40) -> dict[str, Any]:
    toks = re.findall(r"[a-zA-Z]+", (text or "").lower())
    if len(toks) < 2:
        return {"contradiction_proxy_count": 0, "normalized_score": 0.0}
    hits = 0
    for i in range(len(toks)):
        chunk = set(toks[i : i + window])
        if chunk & _POS and chunk & _NEG:
            hits += 1
    n = max(len(toks) - window + 1, 1)
    return {
        "contradiction_proxy_count": hits,
        "normalized_score": round(min(1.0, hits / float(n)), 6),
    }
