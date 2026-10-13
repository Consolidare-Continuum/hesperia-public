# HESPERIA — RAD. P_CH load + concept→hex injection invariants.

from __future__ import annotations

import pytest

import numpy as np

from core.engine.hex_matrix_builders import apply_pch_to_concept_activation
from core.engine.pch_loader import load_pch


def test_load_pch_shape_column_sums_sparsity():
    pch = load_pch()
    assert pch.shape == (72000, 288)
    col_sums = np.asarray(pch.sum(axis=0)).ravel()
    assert np.allclose(col_sums, 1.0, atol=1e-5)
    sp = pch.nnz / float(pch.shape[0] * pch.shape[1])
    assert sp < 0.01


def test_pch_conservation_mass():
    pch = load_pch()
    rng = np.random.RandomState(42)
    a = rng.rand(288).astype(np.float64)
    a = np.maximum(a, 0.0)
    flat = pch @ a
    assert abs(float(flat.sum()) - float(a.sum())) < 1e-5


def test_pch_non_uniform_within_family_row():
    """Single active concept → mass only on its family row; ring is non-uniform."""
    pch = load_pch()
    i = 17
    a = np.zeros(288, dtype=np.float64)
    a[i] = 1.0
    H = apply_pch_to_concept_activation(a, pch, n_hex_per_family=250)
    assert np.allclose(H[:i].sum(), 0.0, atol=1e-12)
    assert np.allclose(H[i + 1 :].sum(), 0.0, atol=1e-12)
    assert float(H[i].sum()) > 0.99
    assert float(np.std(H[i, :])) > 1e-9


def test_pch_two_concepts_differ():
    pch = load_pch()
    a1 = np.zeros(288, dtype=np.float64)
    a1[5] = 1.0
    a2 = np.zeros(288, dtype=np.float64)
    a2[6] = 1.0
    H1 = apply_pch_to_concept_activation(a1, pch)
    H2 = apply_pch_to_concept_activation(a2, pch)
    assert not np.allclose(H1, H2)


def test_missing_pch_manifest_raises(tmp_path):
    empty = tmp_path / "no_pch"
    empty.mkdir()
    with pytest.raises(RuntimeError, match="Missing P_CH"):
        load_pch(empty)


def test_uniform_hex_injection_forbidden_without_dev(monkeypatch):
    monkeypatch.delenv("HESPERIA_PCH_UNIFORM_INJECTION_DEV", raising=False)
    from core.engine.hex_matrix_builders import concept_family_weights_to_hex_source

    with pytest.raises(RuntimeError, match="forbidden"):
        concept_family_weights_to_hex_source([1.0, 2.0, 3.0], n_hex_per_family=5)
