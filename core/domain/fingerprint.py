# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
KME — Domain Fingerprint Engine.
Deterministic fingerprint from PrimitiveMetrics + DerivedMetrics: ordered vector, metadata, vectorHash.
Same input metrics -> same fingerprint bytes.
"""

from __future__ import annotations

import hashlib
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.domain.models import DerivedMetrics, DomainFingerprint, PrimitiveMetrics


FINGERPRINT_VERSION = "hesperia_fp_v0_1"
FP_SCALE = 6
_SCALE_FACTOR = 10**FP_SCALE

PRIMITIVE_ORDER = ["LD", "COH", "NC", "PR", "PV", "CI"]
DERIVED_ORDER = [
    "KDI", "CSI", "SPI", "TDS", "SSS", "KCI", "CCI", "SPS", "DCI", "CSI2",
    "KEF", "ASS", "CDR", "KCR", "TCI",
    "PEI", "KE", "SCS", "CRI", "KNS", "CII", "TEP", "KSI",
    "CDD", "SSR", "TER", "CPC", "KBS", "TRI",
    "IDE", "KPS", "TBI", "KDI2", "CDI", "KVI",
]
FULL_ORDER = PRIMITIVE_ORDER + DERIVED_ORDER

MARKETABLE_DERIVED_ORDER = [
    "KDI", "KNS", "KCR", "KBS",
    "CSI", "TBI", "CDD",
    "TDS", "TCI", "SSS",
    "IDE", "SPS",
    "SPI", "DCI",
]


def marketable_derived_from_map(derived_map: dict[str, float]) -> dict[str, float]:
    """Return only the 14 market-facing derived metrics (round6). Use for dashboards and APIs."""
    return {k: round6(derived_map[k]) for k in MARKETABLE_DERIVED_ORDER if k in derived_map}


def normalize_metric_value(x: float) -> float:
    """All values finite and bounded [0, 1]. NaN/Inf -> 0."""
    if math.isnan(x) or math.isinf(x):
        return 0.0
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def round6(x: float) -> float:
    """Stable rounding to 6 decimal places for serialization and hashing."""
    v = normalize_metric_value(x)
    return round(v * _SCALE_FACTOR) / _SCALE_FACTOR


def format6(x: float) -> str:
    """Fixed 6-decimal string for canonical payload."""
    return f"{round6(x):.6f}"


def safe_string(s: str | None) -> str:
    """Null -> empty; otherwise strip."""
    if s is None:
        return ""
    return s.strip()


def to_primitive_map(p: "PrimitiveMetrics") -> dict[str, float]:
    """Ordered map of primitive names to round6 values."""
    return {
        "LD": round6(p.LD),
        "COH": round6(p.COH),
        "NC": round6(p.NC),
        "PR": round6(p.PR),
        "PV": round6(p.PV),
        "CI": round6(p.CI),
    }


def to_derived_map(d: "DerivedMetrics") -> dict[str, float]:
    """Ordered map of derived names to round6 values."""
    return {
        "KDI": round6(d.KDI),
        "CSI": round6(d.CSI),
        "SPI": round6(d.SPI),
        "TDS": round6(d.TDS),
        "SSS": round6(d.SSS),
        "KCI": round6(d.KCI),
        "CCI": round6(d.CCI),
        "SPS": round6(d.SPS),
        "DCI": round6(d.DCI),
        "CSI2": round6(d.CSI2),
        "KEF": round6(d.KEF),
        "ASS": round6(d.ASS),
        "CDR": round6(d.CDR),
        "KCR": round6(d.KCR),
        "TCI": round6(d.TCI),
        "PEI": round6(d.PEI),
        "KE": round6(d.KE),
        "SCS": round6(d.SCS),
        "CRI": round6(d.CRI),
        "KNS": round6(d.KNS),
        "CII": round6(d.CII),
        "TEP": round6(d.TEP),
        "KSI": round6(d.KSI),
        "CDD": round6(d.CDD),
        "SSR": round6(d.SSR),
        "TER": round6(d.TER),
        "CPC": round6(d.CPC),
        "KBS": round6(d.KBS),
        "TRI": round6(d.TRI),
        "IDE": round6(d.IDE),
        "KPS": round6(d.KPS),
        "TBI": round6(d.TBI),
        "KDI2": round6(d.KDI2),
        "CDI": round6(d.CDI),
        "KVI": round6(d.KVI),
    }


def to_full_vector(p: "PrimitiveMetrics", d: "DerivedMetrics") -> list[float]:
    """Ordered 41-value vector: 6 primitives then 35 derived, each round6."""
    prim = to_primitive_map(p)
    der = to_derived_map(d)
    return [prim[k] for k in PRIMITIVE_ORDER] + [der[k] for k in DERIVED_ORDER]


def metric_names() -> list[str]:
    """Frozen metric name list matching full vector order."""
    return list(FULL_ORDER)


def vector_string(values: list[float]) -> str:
    """Canonical comma-separated string of format6 values."""
    return ",".join(format6(v) for v in values)


def canonical_payload(
    fingerprint_version: str,
    domain_release: str,
    source_id: str,
    values: list[float],
) -> str:
    """Payload for hashing: version|release|sourceId|v1,v2,...,v41."""
    return (
        fingerprint_version
        + "|"
        + safe_string(domain_release)
        + "|"
        + safe_string(source_id)
        + "|"
        + vector_string(values)
    )


def sha256_hex(input_str: str) -> str:
    """SHA-256 digest of UTF-8 input as lowercase hex."""
    return hashlib.sha256(input_str.encode("utf-8")).hexdigest()


def build_fingerprint(
    p: "PrimitiveMetrics",
    d: "DerivedMetrics",
    domain_release: str = "",
    source_id: str = "",
) -> "DomainFingerprint":
    """Build fingerprint from primitives and derived. p and d required."""
    from core.domain.models import DomainFingerprint

    if p is None:
        raise ValueError("PrimitiveMetrics is required")
    if d is None:
        raise ValueError("DerivedMetrics is required")

    version = FINGERPRINT_VERSION
    release = safe_string(domain_release)
    sid = safe_string(source_id)
    names = metric_names()
    values = to_full_vector(p, d)
    prim_map = to_primitive_map(p)
    der_map = to_derived_map(d)
    payload = canonical_payload(version, release, sid, values)
    vector_hash = sha256_hex(payload)

    return DomainFingerprint(
        fingerprint_version=version,
        domain_release=release,
        source_id=sid,
        metric_names=names,
        metric_values=values,
        primitive_map=prim_map,
        derived_map=der_map,
        vector_hash=vector_hash,
    )


def same_fingerprint(a: "DomainFingerprint | None", b: "DomainFingerprint | None") -> bool:
    """Equality by vector hash."""
    if a is None or b is None:
        return False
    return safe_string(a.vector_hash) == safe_string(b.vector_hash)


def euclidean_distance(a: list[float], b: list[float]) -> float:
    """sqrt(sum((a_i - b_i)^2)). Vectors must be same length; uses round6 for stability."""
    if a is None or b is None:
        raise ValueError("Vectors required")
    if len(a) != len(b):
        raise ValueError("Vector size mismatch")
    total = 0.0
    for i in range(len(a)):
        d = round6(a[i]) - round6(b[i])
        total += d * d
    return math.sqrt(total)


def manhattan_distance(a: list[float], b: list[float]) -> float:
    """sum(|a_i - b_i|). Uses round6 for stability."""
    if a is None or b is None:
        raise ValueError("Vectors required")
    if len(a) != len(b):
        raise ValueError("Vector size mismatch")
    total = 0.0
    for i in range(len(a)):
        total += abs(round6(a[i]) - round6(b[i]))
    return total


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """a·b / (||a|| ||b||). Returns value in [-1, 1]; for nonnegative vectors [0, 1]."""
    if a is None or b is None:
        raise ValueError("Vectors required")
    if len(a) != len(b):
        raise ValueError("Vector size mismatch")
    dot = 0.0
    na = 0.0
    nb = 0.0
    for i in range(len(a)):
        x = round6(a[i])
        y = round6(b[i])
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    value = dot / (math.sqrt(na) * math.sqrt(nb))
    return max(-1.0, min(1.0, value))


def band(x: float) -> str:
    """Optional: threshold label for dashboards. Deterministic."""
    v = round6(x)
    if v < 0.20:
        return "very_low"
    if v < 0.40:
        return "low"
    if v < 0.60:
        return "medium"
    if v < 0.80:
        return "high"
    return "very_high"


def label_metrics(names: list[str], values: list[float]) -> dict[str, str]:
    """Optional: metric name -> band label. Deterministic."""
    out: dict[str, str] = {}
    for i in range(min(len(names), len(values))):
        out[names[i]] = band(values[i])
    return out


def build(
    p: "PrimitiveMetrics",
    d: "DerivedMetrics",
    domain_release: str = "",
    source_id: str = "",
) -> "DomainFingerprint":
    """Build fingerprint from primitives and derived."""
    return build_fingerprint(p, d, domain_release, source_id)


def fingerprint_euclidean(a: "DomainFingerprint", b: "DomainFingerprint") -> float:
    """Euclidean distance between two fingerprints' metric vectors."""
    return euclidean_distance(a.metric_values, b.metric_values)


def fingerprint_manhattan(a: "DomainFingerprint", b: "DomainFingerprint") -> float:
    """Manhattan distance between two fingerprints' metric vectors."""
    return manhattan_distance(a.metric_values, b.metric_values)


def fingerprint_cosine(a: "DomainFingerprint", b: "DomainFingerprint") -> float:
    """Cosine similarity between two fingerprints' metric vectors."""
    return cosine_similarity(a.metric_values, b.metric_values)
