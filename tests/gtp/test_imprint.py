# GTP-06 — ThoughtImprint + ImprintDifference + path-discovery pipeline.

from __future__ import annotations

from sphere.topology.gtp.imprint import build_thought_imprint, imprint_difference
from sphere.topology.gtp.neighbors import HexCell
from sphere.topology.gtp.pipeline import gtp_step_to_dict, run_gtp_step
from sphere.topology.gtp.rotation import input_features


def test_thought_imprint_fires_matching_sides() -> None:
    h = HexCell(area_id=0, global_id=3, hex_index=10)
    phi = input_features("this includes and overlaps partially with something")
    imprint = build_thought_imprint(h, phi, hex_rotation=0)
    assert set(imprint.fired_sides) == {0, 3}  # INCLUDES (side 0), OVERLAPS (side 3)


def test_thought_imprint_none_fire_on_unrelated_text() -> None:
    h = HexCell(area_id=0, global_id=3, hex_index=10)
    phi = input_features("zzz yyy xxx www vvv uuu")
    imprint = build_thought_imprint(h, phi, hex_rotation=0)
    assert imprint.fired_sides == ()


def test_imprint_difference_same_baseline_no_shift() -> None:
    h = HexCell(area_id=0, global_id=3, hex_index=10)
    phi = input_features("includes")
    imprint = build_thought_imprint(h, phi, hex_rotation=0)
    diff = imprint_difference(imprint, baseline_area_id=0, baseline_global_id=3)
    assert diff.area_shifted is False
    assert diff.family_shifted is False


def test_imprint_difference_detects_area_and_family_shift() -> None:
    h = HexCell(area_id=1, global_id=25, hex_index=10)
    phi = input_features("includes")
    imprint = build_thought_imprint(h, phi, hex_rotation=0)
    diff = imprint_difference(imprint, baseline_area_id=0, baseline_global_id=3)
    assert diff.area_shifted is True
    assert diff.family_shifted is True


def test_imprint_difference_new_fired_sides_vs_prior() -> None:
    h = HexCell(area_id=0, global_id=3, hex_index=10)
    prior_imprint = build_thought_imprint(h, input_features("includes"), hex_rotation=0)
    current_imprint = build_thought_imprint(
        h, input_features("includes and overlaps"), hex_rotation=0
    )
    diff = imprint_difference(
        current_imprint, baseline_area_id=0, baseline_global_id=3, prior=prior_imprint
    )
    assert diff.new_fired_sides == (3,)  # OVERLAPS newly fired, INCLUDES already in prior


def test_run_gtp_step_end_to_end_deterministic() -> None:
    h = HexCell(area_id=0, global_id=3, hex_index=10)
    text = "this includes and overlaps partially with something"
    r1 = run_gtp_step(text, h, powv_position=(0.3, -0.2, 0.15))
    r2 = run_gtp_step(text, h, powv_position=(0.3, -0.2, 0.15))
    assert gtp_step_to_dict(r1) == gtp_step_to_dict(r2)


def test_gtp_step_to_dict_schema_shape() -> None:
    h = HexCell(area_id=0, global_id=3, hex_index=10)
    result = run_gtp_step("includes", h)
    d = gtp_step_to_dict(result)
    assert d["schema"] == "hesperia.gtp_v0_1"
    assert set(d.keys()) == {
        "schema",
        "hex_rotation",
        "current_hex",
        "thought_imprint",
        "imprint_difference",
        "coherence",
        "gtpa",
    }
