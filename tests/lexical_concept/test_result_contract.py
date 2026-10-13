from __future__ import annotations

from core.result.compare import compare
from core.engine.lexical_concept.pipeline import analyze


def test_result_schema_is_frozen() -> None:
    out = analyze("Structured speech with bounded emotional variance.")
    assert set(out.keys()) == {
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


def test_compare_layer_is_deterministic() -> None:
    a = analyze("Stable session structure and coherent relation tracking.")
    b = analyze("Stable session structure and coherent relation tracking.")
    c = compare(a, b)
    assert c["dominant_match"] is True
    assert c["tension_delta"] == 0.0

