# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""Lightweight opposing-term emphasis without external ML libs."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

_OPP_A = frozenset({"regulation", "security", "control", "tax", "cut", "ban"})
_OPP_B = frozenset({"freedom", "growth", "market", "expansion", "support"})


def run_tfidf_style_baseline(text: str) -> dict[str, Any]:
    toks = re.findall(r"[a-zA-Z]+", (text or "").lower())
    if not toks:
        return {"opposition_score": 0.0}
    tf = Counter(toks)
    n = len(toks)
    max_tf = max(tf.values()) or 1

    def w(t: str) -> float:
        return (tf.get(t, 0) / max_tf) * math.log(1 + n / (1 + tf.get(t, 0)))

    sa = sum(w(t) for t in _OPP_A if t in tf)
    sb = sum(w(t) for t in _OPP_B if t in tf)
    score = min(1.0, (sa * sb) ** 0.5 / 10.0)
    return {"opposition_score": round(score, 6), "weight_a": round(sa, 6), "weight_b": round(sb, 6)}
