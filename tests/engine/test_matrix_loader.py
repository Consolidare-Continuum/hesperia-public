# HESPERIA — Production matrix loader governance.

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from core.engine.matrix_loader import load_production_matrices, resolve_production_matrix_dir


def test_load_production_matrices_smoke():
    m = load_production_matrices()
    assert m["bundle_version"] == "v1"
    assert m["L_F"].shape == (288, 288)
    assert m["C_F"].shape == (288, 288)
    assert m["R_F"].shape == (288, 288)
    assert m["C"] is m["C_F"]
    off = m["C_F"].copy()
    np.fill_diagonal(off, 0.0)
    assert float(np.max(np.abs(off))) > 1e-9


def test_missing_manifest_raises(tmp_path: Path):
    with pytest.raises(RuntimeError, match="Missing production matrix manifest"):
        load_production_matrices(tmp_path)


def test_build_default_matrices_forbidden_without_stub_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("HESPERIA_SEMANTIC_FIELD_STUB_MATRICES", raising=False)
    from hesperia.extensions.dynamics.semantic_field_v1 import build_default_matrices

    with pytest.raises(RuntimeError, match="not allowed in production"):
        build_default_matrices()


def test_contradiction_pressure_positive_with_production_cf():
    """Cross-area C_F + mass in two areas → strictly positive hex Gram contradiction."""
    from core.engine.product_signals import contradiction_pressure_hex

    m = load_production_matrices()
    C_F = m["C_F"]
    rng = np.random.RandomState(42)
    assert contradiction_pressure_hex(rng.rand(288, 12), C_F) > 0.0
    # Deterministic two-area pattern (family 0 vs family 25 → different operational areas)
    A = np.zeros((288, 12), dtype=np.float64)
    A[0, :] = 1.0
    A[25, :] = 0.5
    assert contradiction_pressure_hex(A, C_F) > 0.0
