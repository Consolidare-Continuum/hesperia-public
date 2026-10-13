# GTP-08 — deterministic gold matrix: fixed wording + hex + IPoW -> h*, rotation, side.
#
# Values pinned below were generated once from the current sphere.topology.gtp implementation
# and are re-asserted here as a regression gate — any change to the GTP-01..06 math must
# either keep these stable or update them deliberately (not as an accidental side effect).

from __future__ import annotations

import pytest

from sphere.topology.gtp.neighbors import HexCell
from sphere.topology.gtp.pipeline import gtp_step_to_dict, run_gtp_step

GOLD_CASES: list[tuple[str, str, HexCell, tuple[float, float, float], int, dict, int]] = [
    (
        "includes_overlaps",
        "this includes and overlaps partially with something",
        HexCell(0, 3, 10),
        (0.3, -0.2, 0.15),
        0,
        {"area_id": 10, "global_id": 243, "hex_index": 10},
        0,
    ),
    (
        "excludes_without",
        "excludes everything without any overlap",
        HexCell(5, 125, 0),
        (0.0, 0.0, 0.0),
        1,
        {"area_id": 0, "global_id": 5, "hex_index": 0},
        0,
    ),
    (
        "covers_implies_all",
        "this covers and implies broad coverage for all",
        HexCell(11, 287, 249),
        (-0.4, 0.1, 0.2),
        2,
        {"area_id": 5, "global_id": 143, "hex_index": 249},
        0,
    ),
    (
        "same_identical_equivalent",
        "same identical equal equivalent statement",
        HexCell(3, 80, 125),
        (0.05, 0.05, -0.05),
        5,
        {"area_id": 3, "global_id": 79, "hex_index": 125},
        0,
    ),
    (
        "disjoint_separate",
        "completely disjoint and separate distinct topic",
        HexCell(7, 175, 200),
        (0.6, -0.6, 0.0),
        4,
        {"area_id": 10, "global_id": 247, "hex_index": 200},
        0,
    ),
]


@pytest.mark.parametrize(
    "case_id,text,h,powv_position,expected_rotation,expected_next_hex,expected_exit_side",
    GOLD_CASES,
    ids=[c[0] for c in GOLD_CASES],
)
def test_gtp_gold_matrix(
    case_id, text, h, powv_position, expected_rotation, expected_next_hex, expected_exit_side
) -> None:
    result = run_gtp_step(text, h, powv_position=powv_position)
    d = gtp_step_to_dict(result)
    assert d["hex_rotation"] == expected_rotation
    assert d["gtpa"]["next_hex"] == expected_next_hex
    assert d["gtpa"]["exit_side"] == expected_exit_side


@pytest.mark.parametrize(
    "case_id,text,h,powv_position,expected_rotation,expected_next_hex,expected_exit_side",
    GOLD_CASES,
    ids=[c[0] for c in GOLD_CASES],
)
def test_gtp_gold_matrix_reruns_identically(
    case_id, text, h, powv_position, expected_rotation, expected_next_hex, expected_exit_side
) -> None:
    """Spec §5.2: same input + same pins -> same output, every time."""
    r1 = gtp_step_to_dict(run_gtp_step(text, h, powv_position=powv_position))
    r2 = gtp_step_to_dict(run_gtp_step(text, h, powv_position=powv_position))
    assert r1 == r2
