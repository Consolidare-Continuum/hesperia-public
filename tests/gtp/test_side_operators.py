# GTP-01 — side operator registry invariants.

from __future__ import annotations

import pytest

from sphere.topology.gtp.side_operators import (
    FARA,
    SIDE_SPECS,
    LogicalOperator,
    logical_test,
    side_spec,
    validate_registry,
)


def test_registry_has_exactly_six_sides() -> None:
    assert len(SIDE_SPECS) == 6
    assert {spec.side_id for spec in SIDE_SPECS} == set(range(6))


def test_registry_operators_match_spec_table() -> None:
    expected = [
        LogicalOperator.INCLUDES,
        LogicalOperator.NOT_INCLUDES,
        LogicalOperator.SUBSUMES,
        LogicalOperator.OVERLAPS,
        LogicalOperator.DISJOINT,
        LogicalOperator.EQUIVALENT,
    ]
    assert [spec.logical for spec in SIDE_SPECS] == expected


def test_registry_semantic_ro_en_pairs() -> None:
    expected = [
        ("cu", "with"),
        ("din", "from"),
        ("la", "at"),
        ("spre", "toward"),
        ("dupa", "after"),
        ("pentru", "for"),
    ]
    actual = [(spec.semantic.ro, spec.semantic.en) for spec in SIDE_SPECS]
    assert actual == expected


def test_fara_reserved_stateless() -> None:
    assert FARA.stateless is True
    assert FARA.side_id is None


def test_side_spec_lookup_out_of_range() -> None:
    with pytest.raises(ValueError):
        side_spec(6)


def test_validate_registry_passes() -> None:
    validate_registry()  # must not raise


@pytest.mark.parametrize(
    "op,f,h,expected",
    [
        (LogicalOperator.INCLUDES, frozenset({"a", "b"}), frozenset({"b", "c"}), True),
        (LogicalOperator.INCLUDES, frozenset({"a"}), frozenset({"b"}), False),
        (LogicalOperator.NOT_INCLUDES, frozenset({"a"}), frozenset({"b"}), True),
        (LogicalOperator.SUBSUMES, frozenset({"a", "b", "c"}), frozenset({"a", "b"}), True),
        (LogicalOperator.SUBSUMES, frozenset({"a"}), frozenset({"a", "b"}), False),
        (LogicalOperator.OVERLAPS, frozenset({"a", "b"}), frozenset({"b", "c"}), True),
        (LogicalOperator.OVERLAPS, frozenset({"a", "b"}), frozenset({"a", "b"}), False),
        (LogicalOperator.DISJOINT, frozenset({"a"}), frozenset({"b"}), True),
        (LogicalOperator.DISJOINT, frozenset({"a"}), frozenset({"a"}), False),
        (LogicalOperator.EQUIVALENT, frozenset({"a", "b"}), frozenset({"a", "b"}), True),
        (LogicalOperator.EQUIVALENT, frozenset({"a"}), frozenset({"a", "b"}), False),
    ],
)
def test_logical_test_table(op, f, h, expected) -> None:
    assert logical_test(op, f, h) is expected
