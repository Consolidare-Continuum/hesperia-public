"""DLCR runtime compatibility and degradation helpers."""

from __future__ import annotations

import os


def fallback_enabled() -> bool:
    return os.getenv("HESPERIA_DLCR_FALLBACK", "0") == "1"


def build_degradation_flags(used_fallback: bool, missing_anchor_count: int = 0) -> list[str]:
    flags: list[str] = []
    if used_fallback:
        flags.append("degraded:fallback_word_to_family")
    if missing_anchor_count > 0:
        flags.append(f"degraded:missing_anchor_count={missing_anchor_count}")
    return flags

