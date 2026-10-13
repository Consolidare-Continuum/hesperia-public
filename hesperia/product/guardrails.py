from __future__ import annotations

from typing import Any


def classify_status(text: str, dossier: dict[str, Any]) -> str:
    t = str(text or "").strip()
    if not t:
        return "insufficient_data"
    if len(t) > 20000:
        return "input_too_long"
    alpha = sum(1 for ch in t if ch.isalpha())
    if alpha < max(3, int(len(t) * 0.2)):
        return "noisy_input"
    families = dict(dossier.get("families") or {})
    coverage = sum(float(v) for v in families.values()) if families else 0.0
    if coverage < 0.01:
        return "low_coverage"
    return "ok"

