from __future__ import annotations

from typing import Any


def compress_product_output(metrics: dict[str, Any]) -> dict[str, Any]:
    tension = float(metrics.get("tension", 0.0))
    stability = float(metrics.get("stability", 0.0))
    loopability = float(metrics.get("loopability", 0.0))
    risk = "high" if tension > 0.7 else ("low" if tension < 0.3 else "medium")
    stability_band = "high" if stability > 0.7 else ("low" if stability < 0.4 else "medium")
    pattern = "looping" if loopability > 0.7 else ("coherent" if stability > 0.7 else "fragmented")
    confidence = max(0.0, min(1.0, 0.5 + 0.3 * stability - 0.2 * tension))
    return {
        "risk": risk,
        "stability": stability_band,
        "pattern": pattern,
        "confidence": confidence,
        "decision_basis": {
            "tension": tension,
            "stability": stability,
            "loopability": loopability,
        },
    }

