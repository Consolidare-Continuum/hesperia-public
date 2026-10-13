# HESPERIA — RAD. Phase 1 field dynamics determinism.

from __future__ import annotations

import numpy as np
import pytest

from hesperia.extensions.dynamics import (
    FieldDynamicsState,
    Phase1Theta,
    step_phase1,
)


def test_step_phase1_two_steps_golden():
    th = Phase1Theta()
    s0 = FieldDynamicsState.initial_uniform()
    inj = np.zeros(12)
    inj[0] = 1.0
    z = np.zeros(12)
    s1 = step_phase1(s0, inj, contradiction_signal=z, theta=th)
    s2 = step_phase1(s1, inj, contradiction_signal=z, theta=th)

    np.testing.assert_allclose(s1.area_a[0], 0.3888888888888889, rtol=1e-14, atol=1e-14)
    np.testing.assert_allclose(s1.stab, 0.9490740740740741, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(s2.area_a[0], 0.5509259259259259, rtol=1e-14, atol=1e-14)
    np.testing.assert_allclose(s2.stab, 0.9729938271604939, rtol=1e-12, atol=1e-12)


def test_state_serialization_roundtrip():
    th = Phase1Theta()
    s0 = FieldDynamicsState.initial_uniform()
    s1 = step_phase1(s0, [1.0] + [0.0] * 11, theta=th)
    d = s1.to_serializable()
    s1b = FieldDynamicsState.from_serializable(d)
    np.testing.assert_array_equal(s1.area_a, s1b.area_a)
    np.testing.assert_array_equal(s1.p_a, s1b.p_a)
    assert s1.t == s1b.t and s1.stab == s1b.stab


def test_injection_normalizes():
    th = Phase1Theta(lambda_a=0.0, gamma_f=1.0, gamma_q=0.0, gamma_p=0.0)
    s0 = FieldDynamicsState(
        t=0,
        area_a=np.zeros(12),
        p_a=np.zeros(12),
        stab=1.0,
    )
    # raw would be invalid; after internal normalize, uniform injection
    s1 = step_phase1(s0, [3.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], theta=th)
    np.testing.assert_allclose(s1.area_a.sum(), 1.0)
    assert s1.area_a[0] > s1.area_a[1]
