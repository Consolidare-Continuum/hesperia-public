# tests/cobalt/test_cobalt_branch_facet.py — fpf_bridge_v7_4 §1/§4 branch facet.
from __future__ import annotations

from tools.cobalt_chroma2_attrib_batch import _compute_branch


def test_kernberg_tfp_query_tags_tfp():
    assert _compute_branch("Kernberg's TFP model of borderline personality organization") == "tfp"


def test_russian_perenos_tags_tfp():
    assert _compute_branch("Кернберг перенос и контрперенос при ПРЛ") == "tfp"


def test_unrelated_networking_text_tags_cobalt():
    assert _compute_branch("TCP/IP networking architecture for IoT devices") == "cobalt"


def test_empty_text_defaults_to_cobalt_not_tfp():
    """Conservative default: never guess TFP without a matched term."""
    assert _compute_branch("") == "cobalt"


def test_conservative_default_does_not_mislabel_general_psychology():
    """A generic psychology term alone (not in the seed list) should not tag TFP — this proves
    the classifier stays conservative rather than over-matching on loosely related vocabulary."""
    assert _compute_branch("general cognitive behavioral therapy techniques") == "cobalt"
