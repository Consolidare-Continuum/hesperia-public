# HESPERIA — RAD. Hex-state geometry metrics (Ethan PO-18).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

from __future__ import annotations


def l1_drift(prev: dict[str, float], curr: dict[str, float]) -> float:
    keys = set(prev) | set(curr)
    return sum(abs(float(curr.get(k, 0.0)) - float(prev.get(k, 0.0))) for k in keys)


def active_count(hex_state: dict[str, float]) -> int:
    return sum(1 for v in hex_state.values() if float(v) > 0.0)


def persistence_score(prev: dict[str, float], curr: dict[str, float]) -> float:
    """Overlap mass ratio on active keys (deterministic)."""
    keys = {k for k, v in prev.items() if float(v) > 0} | {k for k, v in curr.items() if float(v) > 0}
    if not keys:
        return 1.0
    num = sum(min(float(prev.get(k, 0.0)), float(curr.get(k, 0.0))) for k in keys)
    den = sum(max(float(prev.get(k, 0.0)), float(curr.get(k, 0.0))) for k in keys) or 1.0
    return num / den
