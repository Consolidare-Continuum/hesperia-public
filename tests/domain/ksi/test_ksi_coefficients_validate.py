"""H62-002 — R_e table has no orphan types vs shipped coefficients."""
from __future__ import annotations

from core.domain.ksi.phi_e import load_relation_type_coefficients


def test_all_shipped_types_have_coefficients() -> None:
    table = load_relation_type_coefficients()
    required = {"activates", "expresses", "co_occurs_with", "observed_in", "defends_against", "opposes", "requires", "inhibits"}
    for t in required:
        assert t in table, f"missing coefficient for {t}"
        assert isinstance(table[t], (int, float))


def test_default_unlisted_fallback() -> None:
    table = load_relation_type_coefficients()
    assert "*" in table or "default_unlisted" in str(table)
