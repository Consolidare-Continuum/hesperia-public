from __future__ import annotations

from core.engine.api import ENGINE_API_VERSION, run_engine_api_v1


def test_engine_api_v1_id_is_frozen() -> None:
    assert ENGINE_API_VERSION == "engine_api_v1"


def test_engine_api_v1_returns_result_envelope() -> None:
    out = run_engine_api_v1("api freeze smoke")
    required = {
        "area_vector",
        "family_vector",
        "dominant_area",
        "dominant_family",
        "tension",
        "loopability",
        "stability",
        "failure_flags",
        "schema_version",
        "fingerprint",
        "deterministic_hash",
    }
    assert required.issubset(set(out.keys()))
