"""Feature flags for IRC Teacher 0.6.3 runtime (Hesperia product repo)."""
from __future__ import annotations

import os


def _env_true(*keys: str, default: str = "0") -> bool:
    for key in keys:
        val = os.environ.get(key)
        if val is not None:
            return val.strip() == "1"
    return default.strip() == "1"


def irc_teacher_enabled() -> bool:
    """IRC-visible Teacher application run."""
    return _env_true("HESPERIA_IRC_TEACHER", "TERSAGOR_HESPERIA_IRC_TEACHER")


def ksi_enabled() -> bool:
    return _env_true("HESPERIA_KSI_ENABLED", default="0")


def engine_enabled() -> bool:
    return _env_true("HESPERIA_ENGINE_ENABLED", "TERSAGOR_HESPERIA_ENGINE_ENABLED", default="1")


def engine_url() -> str:
    return (
        os.environ.get("HESPERIA_ENGINE_URL")
        or os.environ.get("TERSAGOR_HESPERIA_ENGINE_URL")
        or "http://127.0.0.1:18880"
    ).strip()
