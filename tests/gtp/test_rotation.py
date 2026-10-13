# GTP-03 — hex_rotation calibration, side match, determinism.

from __future__ import annotations

from sphere.topology.gtp.rotation import (
    input_features,
    match_logical,
    match_semantic,
    select_hex_rotation,
    side_active,
    side_match_score,
    side_specs_for_rotation,
)
from sphere.topology.gtp.side_operators import LogicalOperator, side_spec


def test_side_active_identity_at_zero_rotation() -> None:
    for k in range(6):
        assert side_active(k, 0) == k


def test_side_active_wraps_mod_6() -> None:
    assert side_active(5, 1) == 0
    assert side_active(0, 5) == 5


def test_match_logical_keyword_hit() -> None:
    phi = input_features("this text includes something")
    assert match_logical(phi, LogicalOperator.INCLUDES) == 1.0
    assert match_logical(phi, LogicalOperator.DISJOINT) == 0.0


def test_match_semantic_ro_and_en() -> None:
    spec = side_spec(0)  # cu / with
    assert match_semantic(input_features("cu ceva"), spec) == 1.0
    assert match_semantic(input_features("with something"), spec) == 1.0
    assert match_semantic(input_features("nothing here"), spec) == 0.0


def test_side_match_score_weights_sum_when_both_hit() -> None:
    spec = side_spec(0)  # INCLUDES / cu-with
    phi = input_features("this includes with something")
    assert side_match_score(phi, spec) == 1.0  # 0.7*1 + 0.3*1


def test_select_hex_rotation_deterministic_same_input() -> None:
    text = "this includes and overlaps partially with something"
    r1, s1 = select_hex_rotation(text)
    r2, s2 = select_hex_rotation(text)
    assert r1 == r2
    assert s1 == s2


def test_select_hex_rotation_returns_valid_range() -> None:
    r, scores = select_hex_rotation("random unrelated text about weather")
    assert 0 <= r <= 5
    assert set(scores.keys()) == set(range(6))


def test_option_b_primary_side_discriminates_includes() -> None:
    """FPF-HSR-14: Option B scores differ by r; INCLUDES+with → r=0."""
    r, scores = select_hex_rotation("this includes with something")
    assert len(set(scores.values())) > 1
    assert r == 0
    assert scores[0] >= max(scores.values())


def test_side_specs_for_rotation_length() -> None:
    specs = side_specs_for_rotation(3)
    assert len(specs) == 6
    assert [s.side_id for s in specs] == [(k + 3) % 6 for k in range(6)]
