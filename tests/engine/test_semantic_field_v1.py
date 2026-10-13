# HESPERIA — RAD. SEMANTIC_FIELD_EQUATIONS_v1 contract tests.

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from core.layers.layer_2 import build_canonical_stub_adjacency
from hesperia.extensions.dynamics.semantic_field_v1 import (
    NUM_AREAS,
    NUM_FAMILIES,
    SPEC_ID,
    aggregate_source_vectors,
    build_contradiction_matrix,
    build_default_matrices,
    build_family_adjacency_from_sets,
    build_family_laplacian,
    build_resistance_matrix,
    compute_convergence_metrics,
    compute_field_energy_linear,
    compute_observables,
    load_semantic_field_params_v1,
    project_family_to_area,
    semantic_field_e2e_bundle,
    source_from_hits_normalized,
    step_field_euler,
)


def test_calibration_loads():
    p = load_semantic_field_params_v1()
    assert p.alpha > 0 and p.beta > 0 and p.dt > 0
    assert SPEC_ID in p.spec_id or p.spec_id == SPEC_ID
    meta = p.to_metadata()
    assert "epsilon" in meta


def test_adjacency_laplacian_symmetric_nonneg():
    adj = build_canonical_stub_adjacency(NUM_FAMILIES, NUM_AREAS)
    w = build_family_adjacency_from_sets(adj)
    assert w.shape == (NUM_FAMILIES, NUM_FAMILIES)
    assert (w >= 0).all()
    assert np.allclose(w, w.T)
    l_f = build_family_laplacian(w)
    assert l_f.shape == w.shape


def test_contradiction_zero_diag():
    x = np.ones((NUM_FAMILIES, NUM_FAMILIES)) * 0.1
    c = build_contradiction_matrix(x)
    assert np.allclose(np.diag(c), 0)


def test_step_clip_bounded():
    mats = build_default_matrices()
    f = np.full(NUM_FAMILIES, 0.5)
    s = source_from_hits_normalized([1] + [0] * (NUM_FAMILIES - 1))
    p = load_semantic_field_params_v1()
    fn, diag = step_field_euler(f, s, mats["L_F"], mats["R_F"], mats["C"], params=p)
    assert (fn >= 0).all() and (fn <= 1).all()
    assert "delta_f_norm_l2" in diag


def test_area_projection_sum():
    f = np.arange(NUM_FAMILIES, dtype=np.float64) * 0.001
    a = project_family_to_area(f)
    assert a.shape == (NUM_AREAS,)
    assert abs(a.sum() - f.sum()) < 1e-9


def test_observables_and_energy():
    mats = build_default_matrices()
    f0 = np.full(NUM_FAMILIES, 1.0 / NUM_FAMILIES)
    s = f0.copy()
    p = load_semantic_field_params_v1()
    f1, _ = step_field_euler(f0, s, mats["L_F"], mats["R_F"], mats["C"], params=p)
    obs = compute_observables(f0, f1, s, mats["L_F"], mats["R_F"], mats["C"], dt=p.dt)
    assert "propagation_velocity_v" in obs
    assert "stability_sigma" in obs
    e = compute_field_energy_linear(f0, s, mats["L_F"], mats["R_F"], mats["C"], params=p)
    assert isinstance(e, float)


def test_convergence_flags():
    mats = build_default_matrices()
    f = np.full(NUM_FAMILIES, 0.01)
    fn = f.copy()
    m = compute_convergence_metrics(f, fn, mats["C"])
    assert m["numerically_stable"] is True
    assert m["contradiction_stable"] is True


def test_aggregate_documents():
    p = load_semantic_field_params_v1()
    v = np.zeros(NUM_FAMILIES)
    v[0] = 1.0
    s, meta = aggregate_source_vectors(
        [{"source_vector": v.tolist(), "q": 1.0, "t": 0.0}],
        t_ref=10.0,
        params=p,
    )
    assert s[0] > 0
    assert "document_weights" in meta


def test_e2e_bundle_keys():
    hits = [0] * NUM_FAMILIES
    hits[5] = 10
    b = semantic_field_e2e_bundle(source_288=hits, hits_as_source=True, n_steps=2)
    assert b["spec_id"] == SPEC_ID
    assert str(b.get("matrices_provenance", "")).startswith("production_bundle")
    assert "field_state" in b and "field_state_next" in b
    assert b["field_timeline"] is not None
    assert len(b["field_timeline"]) == 2
    assert "field_observables" in b["field_timeline"][0]


def test_calibration_json_exists():
    root = Path(__file__).resolve().parents[2]
    cal = root / "assets" / "calibration" / "semantic_field_equations_v1.json"
    assert cal.is_file()
    data = json.loads(cal.read_text(encoding="utf-8"))
    assert "parameters" in data or "alpha" in str(data)
