# HESPERIA — TFP grain-12 profile path (TFP-POLES-03).
# Default TFP analyze profile pins grain=10 (ten-area pack). Poles / CHI-003
# re-baseline needs an explicit grain-12 path without changing sealed AREAS=12.

from __future__ import annotations

import os
from typing import Any

GRAIN12_ENV = "HESPERIA_AREA_MATH_GRAIN"
TFP_GRAIN12_PROFILE_ID = "tfp_grain12_poles_v0"


def tfp_grain12_enabled() -> bool:
    raw = (os.environ.get(GRAIN12_ENV) or "").strip()
    return raw == "12"


def apply_tfp_grain12_profile_env(*, force: bool = False) -> dict[str, str]:
    """
    Opt-in process env for TFP + grain-12 (poles / full sphere projection).
    Does not alter sealed AREAS=12 ontology. Does not flip analyze profile itself.
    """
    applied: dict[str, str] = {}
    if force or not (os.environ.get(GRAIN12_ENV) or "").strip():
        os.environ[GRAIN12_ENV] = "12"
        applied[GRAIN12_ENV] = "12"
    if not (os.environ.get("HESPERIA_ANALYZE_PROFILE") or "").strip():
        os.environ["HESPERIA_ANALYZE_PROFILE"] = "tfp"
        applied["HESPERIA_ANALYZE_PROFILE"] = "tfp"
    return applied


def grain12_profile_meta() -> dict[str, Any]:
    return {
        "profile_id": TFP_GRAIN12_PROFILE_ID,
        "area_math_grain": 12,
        "sealed_areas": 12,
        "note": "grain is projection/classifier; AREAS ontology stays 12 (Tier D sealed)",
        "chi003_rebaseline": "use grain=12 for pole A11/A12 mass + inhibition; do not confuse with AREAS=10",
    }
