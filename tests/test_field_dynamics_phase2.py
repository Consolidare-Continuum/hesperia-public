# HESPERIA — RAD. Ethan Phase 2 — L5 family + L6 blend.

from __future__ import annotations

import numpy as np
import pytest

from hesperia.extensions.dynamics.phase2 import step_phase2
from hesperia.extensions.dynamics.state import FieldDynamicsState, Phase2Theta


def test_step_phase2_updates_family_and_area():
    s0 = FieldDynamicsState.initial_uniform()
    hit_12 = [1.0] + [0.0] * 11
    fam = [0.0] * 288
    fam[0] = 1.0
    z = [0.0] * 12
    s1 = step_phase2(s0, hit_12, fam, contradiction_signal_area=z, theta2=Phase2Theta(area_hit_weight=0.9))
    assert s1.t == 1
    assert s1.f_f.sum() == pytest.approx(1.0)
    assert s1.f_f[0] > s1.f_f[100]
    assert len(s1.p_family) == 288


def test_step_phase2_family_pressure_from_contradiction():
    s0 = FieldDynamicsState.initial_uniform()
    hit = [1.0 / 12] * 12
    fam = [1.0 / 288] * 288
    c_sig = [0.0] * 12
    c_sig[0] = 1.0
    s1 = step_phase2(s0, hit, fam, contradiction_signal_area=c_sig)
    block0 = float(s1.p_family[:24].sum())
    block1 = float(s1.p_family[24:48].sum())
    assert block0 > block1


def test_phase2_deterministic_replay():
    s0 = FieldDynamicsState.initial_uniform()
    th2 = Phase2Theta()
    a = step_phase2(s0, [1.0] + [0.0] * 11, [1.0 / 288] * 288, theta2=th2)
    b = step_phase2(s0, [1.0] + [0.0] * 11, [1.0 / 288] * 288, theta2=th2)
    np.testing.assert_array_equal(a.area_a, b.area_a)
    np.testing.assert_array_equal(a.f_f, b.f_f)
