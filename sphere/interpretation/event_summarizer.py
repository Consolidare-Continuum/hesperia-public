# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""
Layer-10 event summarizer: flatten Layer-9 events into canonical names and build summary.
"""

from __future__ import annotations

from typing import Any


def extract_active_events(logic_metrics: dict[str, Any]) -> list[str]:
    """Flatten Layer-9 triggered_rules into a list of canonical event type names."""
    triggered = logic_metrics.get("triggered_rules") or []
    names: list[str] = []
    seen: set[str] = set()
    for e in triggered:
        if not isinstance(e, dict):
            continue
        t = e.get("type")
        if t and t not in seen:
            seen.add(t)
            names.append(t)
    return names


def build_event_summary(logic_metrics: dict[str, Any]) -> dict[str, Any]:
    """Summarize counts and groups of events from logic_metrics."""
    triggered = logic_metrics.get("triggered_rules") or []
    by_type: dict[str, int] = {}
    for e in triggered:
        if not isinstance(e, dict):
            continue
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "total_triggered": len(triggered),
        "by_type": by_type,
        "dominance_events_count": len(logic_metrics.get("dominance_events") or []),
        "entropy_events_count": len(logic_metrics.get("entropy_events") or []),
        "tension_events_count": len(logic_metrics.get("tension_events") or []),
    }
