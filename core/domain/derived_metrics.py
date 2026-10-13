# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
KME — Derived Metric Engine.
Thirty-five derived metrics from six primitives. Strict bounded regime: clamp01, safeDiv.
Pure algebra over primitives only; no graph access.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.domain.models import DerivedMetrics, PrimitiveMetrics


def clamp01(x: float) -> float:
    """Clamp to [0, 1]. NaN and Infinity -> 0.0."""
    if math.isnan(x) or math.isinf(x):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def safe_div(numerator: float, denominator: float) -> float:
    """Safe division: invalid inputs or denominator <= 0 -> 0.0."""
    if math.isnan(numerator) or math.isinf(numerator):
        return 0.0
    if math.isnan(denominator) or math.isinf(denominator):
        return 0.0
    if denominator <= 0.0:
        return 0.0
    return numerator / denominator


def zero_derived_metrics() -> "DerivedMetrics":
    """Return all 35 derived metrics set to 0.0."""
    from core.domain.models import DerivedMetrics

    return DerivedMetrics(
        KDI=0.0, CSI=0.0, SPI=0.0, TDS=0.0, SSS=0.0, KCI=0.0, CCI=0.0, SPS=0.0,
        DCI=0.0, CSI2=0.0, KEF=0.0, ASS=0.0, CDR=0.0, KCR=0.0, TCI=0.0,
        PEI=0.0, KE=0.0, SCS=0.0, CRI=0.0, KNS=0.0, CII=0.0, TEP=0.0, KSI=0.0,
        CDD=0.0, SSR=0.0, TER=0.0, CPC=0.0, KBS=0.0, TRI=0.0,
        IDE=0.0, KPS=0.0, TBI=0.0, KDI2=0.0, CDI=0.0, KVI=0.0,
    )


def compute_derived_metrics(p: "PrimitiveMetrics | None") -> "DerivedMetrics":
    """Full derived calculator. Null input -> zero metrics. All outputs clamp01."""
    from core.domain.models import DerivedMetrics

    if p is None:
        return zero_derived_metrics()

    LD = clamp01(p.LD)
    COH = clamp01(p.COH)
    NC = clamp01(p.NC)
    PR = clamp01(p.PR)
    PV = clamp01(p.PV)
    CI = clamp01(p.CI)

    return DerivedMetrics(
        KDI=clamp01(LD * COH),
        CSI=clamp01(NC * PR),
        SPI=clamp01(CI),
        TDS=clamp01(PR * LD),
        SSS=clamp01(safe_div(COH, PV)),
        KCI=clamp01(safe_div(LD, PR)),
        CCI=clamp01(COH * NC),
        SPS=clamp01(PR * COH),
        DCI=clamp01(LD * NC),
        CSI2=clamp01(CI * LD),
        KEF=clamp01(safe_div(PV, NC)),
        ASS=clamp01(safe_div(COH * LD, PV)),
        CDR=clamp01(safe_div(PR, NC)),
        KCR=clamp01(safe_div(LD, NC)),
        TCI=clamp01(COH * LD * CI),
        PEI=clamp01(safe_div(PR, PV)),
        KE=clamp01(safe_div(PR, LD)),
        SCS=clamp01(safe_div(LD * COH, NC)),
        CRI=clamp01(CI * COH),
        KNS=clamp01(NC * COH * LD),
        CII=clamp01(safe_div(NC, PR)),
        TEP=clamp01(PV * LD),
        KSI=clamp01(safe_div(COH * LD, PR)),
        CDD=clamp01(safe_div(NC, PV)),
        SSR=clamp01(safe_div(PR, PV)),
        TER=clamp01(safe_div(CI, LD)),
        CPC=clamp01(safe_div(PR * NC, PV)),
        KBS=clamp01(safe_div(COH * NC, PV)),
        TRI=clamp01(safe_div(CI * LD, PR)),
        IDE=clamp01(safe_div(PR * COH, NC)),
        KPS=clamp01(safe_div(COH, PR)),
        TBI=clamp01(NC * PV),
        KDI2=clamp01(LD * PR * COH),
        CDI=clamp01(CI * NC),
        KVI=clamp01(safe_div(LD * COH * PR, PV)),
    )


def to_derived_vector(d: "DerivedMetrics") -> list[float]:
    """Stable vector of 35 derived metrics in canonical order."""
    return [
        d.KDI, d.CSI, d.SPI, d.TDS, d.SSS, d.KCI, d.CCI, d.SPS, d.DCI, d.CSI2,
        d.KEF, d.ASS, d.CDR, d.KCR, d.TCI,
        d.PEI, d.KE, d.SCS, d.CRI, d.KNS, d.CII, d.TEP, d.KSI,
        d.CDD, d.SSR, d.TER, d.CPC, d.KBS, d.TRI,
        d.IDE, d.KPS, d.TBI, d.KDI2, d.CDI, d.KVI,
    ]


def to_full_fingerprint(
    p: "PrimitiveMetrics | None",
    d: "DerivedMetrics | None",
) -> list[float]:
    """Full 41-signal fingerprint: 6 primitives then 35 derived in canonical order."""
    if p is None and d is None:
        return [0.0] * 6 + [0.0] * 35
    prim = [0.0] * 6
    if p is not None:
        prim = [p.LD, p.COH, p.NC, p.PR, p.PV, p.CI]
    der = [0.0] * 35
    if d is not None:
        der = to_derived_vector(d)
    return prim + der


def compute(p: "PrimitiveMetrics | None") -> "DerivedMetrics":
    """Entry point: compute derived metrics from primitives."""
    return compute_derived_metrics(p)


def vector(d: "DerivedMetrics") -> list[float]:
    """Entry point: derived metrics as stable vector."""
    return to_derived_vector(d)


def full_fingerprint(p: "PrimitiveMetrics | None", d: "DerivedMetrics | None") -> list[float]:
    """Entry point: 41-signal fingerprint (6 primitives + 35 derived)."""
    return to_full_fingerprint(p, d)
