# HESPERIA — RAD. Hex → family bridge.

from __future__ import annotations

import numpy as np

from core.engine.hex_family_bridge import (
    compute_family_activation,
    default_hex_family_weight_matrix_2d,
    parse_hex_id_to_linear_index,
)


def test_parse_hex_id():
    u = parse_hex_id_to_linear_index("A3_F12_H05")
    assert u == (2 * 24 + 11) * 250 + 4


def test_singleton_aggregation():
    nf, nh = 4, 5
    a = np.arange(nf * nh, dtype=np.float64).reshape(nf, nh)
    f = compute_family_activation(a, n_families=nf, n_hex_per_family=nh)
    assert np.allclose(f, a.sum(axis=1))


def test_weight_matrix_path():
    nf, nh = 3, 4
    w = default_hex_family_weight_matrix_2d(nf, nh)
    a = np.ones(nf * nh)
    f = compute_family_activation(a, weight_matrix=w)
    assert np.allclose(f, np.full(nf, nh))
