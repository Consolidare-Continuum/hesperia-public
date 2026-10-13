# HESPERIA — RAD. Ontology-derived field matrices.

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from hesperia.extensions.dynamics.matrix_builders import (
    build_contradiction_matrix,
    build_family_adjacency_matrix,
    build_family_index,
    build_resistance_vector,
)


def test_build_family_index_sorted():
    idx = build_family_index(["Z", "A", "M"])
    assert idx == {"A": 0, "M": 1, "Z": 2}


def test_family_adjacency():
    families = ["A", "B", "C"]

    relations = [
        ("A", "B"),
        ("B", "C"),
    ]

    w = build_family_adjacency_matrix(families, relations)

    assert w.shape == (3, 3)
    idx = build_family_index(families)
    ia, ib, ic = idx["A"], idx["B"], idx["C"]
    assert w[ia, ib] == 1
    assert w[ib, ic] == 1


def test_contradiction_matrix():
    families = ["A", "B"]

    contradictions = [
        ("A", "B", 0.7),
    ]

    c = build_contradiction_matrix(families, contradictions)

    idx = build_family_index(families)
    ia, ib = idx["A"], idx["B"]
    assert c[ia, ib] == 0.7
    assert c[ib, ia] == 0.7


def test_resistance_vector():
    families = ["A", "B"]

    priors = {"A": 0.5}

    r = build_resistance_vector(families, priors)

    idx = build_family_index(families)
    ia, ib = idx["A"], idx["B"]
    assert r[ia] == 0.5
    assert r[ib] == 0.1


def _load_run_semantic_field():
    import importlib.util

    path = _REPO / "runtime" / "semantic_field" / "run_semantic_field.py"
    spec = importlib.util.spec_from_file_location("hesperia_run_sf", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_resolve_semantic_field_matrices_ontology():
    mod = _load_run_semantic_field()
    resolve_semantic_field_matrices = mod.resolve_semantic_field_matrices

    cfg = {
        "family_count": 3,
        "ontology": {
            "family_ids": ["x", "y", "z"],
            "relations": [["x", "y"], ["y", "z"]],
            "contradictions": [["x", "z", 0.5]],
            "resistance_priors": {"x": 0.3},
            "resistance_default": 0.15,
        },
    }
    w, rvec, c, id_map, prov = resolve_semantic_field_matrices(cfg)
    assert prov == "ontology"
    assert w.shape == (3, 3)
    assert id_map is not None
    assert "x" in id_map
    assert rvec.shape == (3,)
    assert c.shape == (3, 3)


def test_run_semantic_field_with_ontology_block():
    mod = _load_run_semantic_field()
    run_semantic_field = mod.run_semantic_field

    cfg = {
        "family_count": 2,
        "families_per_area": 1,
        "area_count": 2,
        "ontology": {
            "family_ids": ["fam_a", "fam_b"],
            "relations": [["fam_a", "fam_b"]],
            "contradictions": [],
            "resistance_default": 0.1,
        },
        "alpha": 0.1,
        "beta": 0.05,
        "gamma": 0.0,
        "delta": 0.3,
        "dt": 1.0,
        "epsilon": 1e-3,
        "tau": 1e-3,
        "initial_mode": "uniform",
        "documents": [{"source_family_id": "fam_a", "source_strength": 1.0}],
        "max_steps": 5,
    }
    out = run_semantic_field(cfg)
    assert out["matrices_provenance"] == "ontology"
    assert len(out["family_field_final"]) == 2
    assert "family_id_index" in out
