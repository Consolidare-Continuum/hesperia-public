# Unmapped token diagnostics (HC-08) — ranked reports, no dict mutation. Copyright © 2026 igareosh.com.
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UnmappedDiagnosticsReport:
    """Diagnostic bundle; engine does not write dictionaries."""

    ranked_by_frequency: list[tuple[str, int]] = field(default_factory=list)
    flags: dict[str, list[str]] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


def rank_unmapped_tokens(
    token_counts: dict[str, int],
    *,
    limit: int = 50,
) -> UnmappedDiagnosticsReport:
    """Deterministic sort: count desc, then token asc."""
    ranked = sorted(token_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    flags = {t: ["needs_review"] for t, _ in ranked}
    return UnmappedDiagnosticsReport(ranked_by_frequency=ranked, flags=flags, meta={"limit": limit})
