# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""Tests for Task 4 — Derived Metric Engine. Acceptance tests A–E."""

from __future__ import annotations

import math

import pytest

from core.domain.models import PrimitiveMetrics
from core.domain.derived_metrics import (
    clamp01,
    safe_div,
    compute_derived_metrics,
    zero_derived_metrics,
    to_derived_vector,
    to_full_fingerprint,
)


# ---------------------------------------------------------------------------
# Test A — Null Input
# ---------------------------------------------------------------------------
def test_null_input_all_zeros() -> None:
    """PrimitiveMetrics p = null -> all derived metrics = 0.0."""
    out = compute_derived_metrics(None)
    assert out.KDI == 0.0 and out.CSI == 0.0 and out.SPI == 0.0
    assert out.TCI == 0.0 and out.KVI == 0.0
    vec = to_derived_vector(out)
    assert len(vec) == 35
    assert all(v == 0.0 for v in vec)


# ---------------------------------------------------------------------------
# Test B — All-Zero Primitive Vector
# ---------------------------------------------------------------------------
def test_all_zero_primitives_all_derived_zero() -> None:
    """LD=COH=NC=PR=PV=CI=0 -> all derived = 0.0."""
    p = PrimitiveMetrics(LD=0.0, COH=0.0, NC=0.0, PR=0.0, PV=0.0, CI=0.0)
    out = compute_derived_metrics(p)
    assert out.KDI == 0.0 and out.CSI == 0.0 and out.SPI == 0.0
    assert out.SSS == 0.0 and out.KEF == 0.0 and out.TBI == 0.0
    assert out.KVI == 0.0
    assert to_derived_vector(out) == [0.0] * 35


# ---------------------------------------------------------------------------
# Test C — Fully Bounded Input (all ones)
# ---------------------------------------------------------------------------
def test_all_ones_primitives_expected_ones() -> None:
    """LD=COH=NC=PR=PV=CI=1 -> multiplicative metrics = 1, division-based = 1."""
    p = PrimitiveMetrics(LD=1.0, COH=1.0, NC=1.0, PR=1.0, PV=1.0, CI=1.0)
    out = compute_derived_metrics(p)
    # Multiplication-based
    assert out.KDI == 1.0 and out.CSI == 1.0 and out.SPI == 1.0
    assert out.TDS == 1.0 and out.CCI == 1.0 and out.SPS == 1.0
    assert out.DCI == 1.0 and out.CSI2 == 1.0 and out.TCI == 1.0
    assert out.KNS == 1.0 and out.TEP == 1.0 and out.TBI == 1.0
    assert out.KDI2 == 1.0 and out.CDI == 1.0
    # Division-based (1/1 = 1, clamp 1)
    assert out.SSS == 1.0 and out.KCI == 1.0 and out.KEF == 1.0
    assert out.ASS == 1.0 and out.CDR == 1.0 and out.KCR == 1.0
    assert out.PEI == 1.0 and out.KE == 1.0 and out.SCS == 1.0
    assert out.CII == 1.0 and out.KSI == 1.0
    assert out.CDD == 1.0 and out.SSR == 1.0 and out.TER == 1.0
    assert out.CPC == 1.0 and out.KBS == 1.0 and out.TRI == 1.0
    assert out.IDE == 1.0 and out.KPS == 1.0 and out.KVI == 1.0


# ---------------------------------------------------------------------------
# Test D — Zero Denominator Cases
# ---------------------------------------------------------------------------
def test_zero_denominator_cases_no_nan() -> None:
    """NC=0, PV=0 -> SSS, ASS, KEF, CDD, SSR, CPC, KBS, KVI = 0. No NaN/Inf."""
    p = PrimitiveMetrics(LD=0.7, COH=0.8, NC=0.0, PR=0.4, PV=0.0, CI=0.2)
    out = compute_derived_metrics(p)
    assert out.SSS == 0.0
    assert out.ASS == 0.0
    assert out.KEF == 0.0
    assert out.CDD == 0.0
    assert out.SSR == 0.0
    assert out.CPC == 0.0
    assert out.KBS == 0.0
    assert out.KVI == 0.0
    d = out.to_dict()
    for k, v in d.items():
        assert not math.isnan(v), f"{k} is NaN"
        assert not math.isinf(v), f"{k} is Inf"


# ---------------------------------------------------------------------------
# Test E — Monotonic Direction Checks
# ---------------------------------------------------------------------------
def test_monotonic_ld_increase() -> None:
    """If LD increases and all else fixed: KDI, DCI, CSI2, TCI, TEP should not decrease."""
    base = PrimitiveMetrics(LD=0.3, COH=0.5, NC=0.4, PR=0.4, PV=0.5, CI=0.3)
    high_ld = PrimitiveMetrics(LD=0.8, COH=0.5, NC=0.4, PR=0.4, PV=0.5, CI=0.3)
    o1 = compute_derived_metrics(base)
    o2 = compute_derived_metrics(high_ld)
    assert o2.KDI >= o1.KDI
    assert o2.DCI >= o1.DCI
    assert o2.CSI2 >= o1.CSI2
    assert o2.TCI >= o1.TCI
    assert o2.TEP >= o1.TEP


def test_monotonic_coh_increase() -> None:
    """If COH increases and all else fixed: KDI, CCI, SPS, CRI, KPS should not decrease."""
    base = PrimitiveMetrics(LD=0.5, COH=0.3, NC=0.4, PR=0.4, PV=0.5, CI=0.2)
    high_coh = PrimitiveMetrics(LD=0.5, COH=0.9, NC=0.4, PR=0.4, PV=0.5, CI=0.2)
    o1 = compute_derived_metrics(base)
    o2 = compute_derived_metrics(high_coh)
    assert o2.KDI >= o1.KDI
    assert o2.CCI >= o1.CCI
    assert o2.SPS >= o1.SPS
    assert o2.CRI >= o1.CRI
    assert o2.KPS >= o1.KPS


def test_monotonic_pv_increase_ratios_decrease() -> None:
    """If PV increases (numerators fixed): SSS, ASS, PEI, CDD, SSR should not increase."""
    base = PrimitiveMetrics(LD=0.5, COH=0.6, NC=0.4, PR=0.4, PV=0.2, CI=0.2)
    high_pv = PrimitiveMetrics(LD=0.5, COH=0.6, NC=0.4, PR=0.4, PV=0.9, CI=0.2)
    o1 = compute_derived_metrics(base)
    o2 = compute_derived_metrics(high_pv)
    # SSS = COH/PV: when PV increases, SSS decreases
    assert o2.SSS <= o1.SSS
    # ASS = (COH*LD)/PV
    assert o2.ASS <= o1.ASS
    # PEI = PR/PV
    assert o2.PEI <= o1.PEI
    # CDD = NC/PV
    assert o2.CDD <= o1.CDD
    # SSR = PR/PV
    assert o2.SSR <= o1.SSR


# ---------------------------------------------------------------------------
# Utilities and vector/fingerprint
# ---------------------------------------------------------------------------
def test_clamp01_nan_inf() -> None:
    assert clamp01(float("nan")) == 0.0
    assert clamp01(float("inf")) == 0.0
    assert clamp01(-float("inf")) == 0.0
    assert clamp01(0.5) == 0.5
    assert clamp01(-0.1) == 0.0
    assert clamp01(1.5) == 1.0


def test_safe_div() -> None:
    assert safe_div(1.0, 2.0) == 0.5
    assert safe_div(1.0, 0.0) == 0.0
    assert safe_div(1.0, -1.0) == 0.0
    assert safe_div(float("nan"), 1.0) == 0.0
    assert safe_div(1.0, float("inf")) == 0.0


def test_to_derived_vector_order() -> None:
    z = zero_derived_metrics()
    vec = to_derived_vector(z)
    assert len(vec) == 35
    assert vec[0] == z.KDI and vec[1] == z.CSI and vec[34] == z.KVI


def test_to_full_fingerprint_length_and_order() -> None:
    p = PrimitiveMetrics(LD=0.1, COH=0.2, NC=0.3, PR=0.4, PV=0.5, CI=0.6)
    d = compute_derived_metrics(p)
    fp = to_full_fingerprint(p, d)
    assert len(fp) == 41
    assert fp[0] == p.LD and fp[1] == p.COH and fp[5] == p.CI
    assert fp[6] == d.KDI and fp[40] == d.KVI


def test_full_fingerprint_null() -> None:
    fp = to_full_fingerprint(None, None)
    assert len(fp) == 41
    assert all(v == 0.0 for v in fp)


def test_derived_metrics_to_dict_canonical_order() -> None:
    from core.domain.models import DerivedMetrics

    z = zero_derived_metrics()
    d = z.to_dict()
    keys = list(d.keys())
    assert keys[0] == "KDI" and keys[34] == "KVI"
    assert len(keys) == 35
