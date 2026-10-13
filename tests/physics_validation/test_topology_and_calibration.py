# Governed topology + calibration bundles

from __future__ import annotations

from hesperia.engine.calibration_profile import load_calibration_profile, semantic_field_params_from_profile
from core.engine.hex_topology_authority import neighbor_global_hex_ids, validate_topology_invariants
from hesperia.ontology.concept_registry import n_concept_canon


def test_hex_topology_manifest_matches_invariants():
    validate_topology_invariants()
    u = 37 * 250 + 10
    a, b = neighbor_global_hex_ids(u)
    assert a != b


def test_calibration_profile_load_default():
    p = load_calibration_profile()
    assert "alpha" in p and "dt" in p
    sp = semantic_field_params_from_profile()
    assert sp.dt > 0


def test_n_concept_canon_is_288():
    assert n_concept_canon() == 288
