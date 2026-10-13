# HESPERIA COBALT feature flags.
from __future__ import annotations

import os


def cobalt_enabled() -> bool:
    return os.environ.get("HESPERIA_COBALT_ENABLED", "0").strip() in ("1", "true", "yes", "on")


def chroma2_url() -> str:
    return os.environ.get(
        "HESPERIA_CHROMA2_URL",
        "http://chroma-2.prichindel.local:8002",
    ).strip().rstrip("/")


def cobalt_top_k() -> int:
    try:
        return max(1, min(20, int(os.environ.get("HESPERIA_COBALT_TOP_K", "5"))))
    except ValueError:
        return 5
