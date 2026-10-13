# HESPERIA — RAD. Phase 3 L4 active hex (family-proxy).

from __future__ import annotations

import numpy as np
import pytest

from hesperia.extensions.dynamics.phase3 import (
    area_vector_from_hex,
    step_phase3,
    family_vector_from_hex,
)
from hesperia.extensions.dynamics.state import FieldDynamicsState, Phase3Theta


def test_step_phase3_creates_sparse_hex():
    s0 = FieldDynamicsState.initial_uniform()
    hits = [0] * 288
    hits[5] = 3
    hits[6] = 2
    s1 = step_phase3(s0, hits, [0.0] * 12, theta=Phase3Theta(hex_cap=16))
    assert "5" in s1.hex_x or "6" in s1.hex_x
    assert len(s1.hex_x) <= 16
    assert s1.t == s0.t


def test_step_phase3_respects_cap():
    hits = [1] * 288
    s0 = FieldDynamicsState.initial_uniform()
    s1 = step_phase3(s0, hits, [0.0] * 12, theta=Phase3Theta(hex_cap=20))
    assert len(s1.hex_x) <= 20


def test_family_vector_from_hex():
    hx = {"0": 0.5, "1": 0.5}
    v = family_vector_from_hex(hx)
    assert v.sum() == pytest.approx(1.0)
    assert v[0] > v[100]


def test_area_vector_from_hex():
    hx = {str(i): 1.0 for i in range(24)}
    a = area_vector_from_hex(hx)
    assert a[0] > 0.99
    assert a[1] < 0.01
