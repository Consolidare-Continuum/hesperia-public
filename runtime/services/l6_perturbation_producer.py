# HESPERIA — /analyze L6 perturbation producer (flag-gated; Class A).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Produce measured E(x±ε) Layer-1 snapshots for Layer-6 finite differences.

Default off via ``HESPERIA_L6_PERTURBATION``. Does not invent formulas: re-runs
``compute_L1`` / ``compute_L2`` on hit-count perturbations of the sealed base run.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from core.layers.layer_1 import compute_L1
from core.layers.layer_2 import compute_L2
from core.layers.layer_6 import compute_L6

_TRUTHY = ("1", "true", "yes", "on")
_DEFAULT_EPSILON = 0.05
_L1_KEYS = (
    "COVERAGE_RATIO",
    "FAMILY_ENTROPY",
    "DOMINANCE_RATIO",
    "DOMINANT_FAMILY_ID",
    "NORMALIZED_FAMILY_ENTROPY",
)


def l6_perturbation_enabled() -> bool:
    return os.environ.get("HESPERIA_L6_PERTURBATION", "0").strip().lower() in _TRUTHY


def _epsilon_magnitude() -> float:
    raw = os.environ.get("HESPERIA_L6_PERTURBATION_EPS", "").strip()
    if not raw:
        return _DEFAULT_EPSILON
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_EPSILON
    return value if value > 0.0 else _DEFAULT_EPSILON


def _matched_from_hits(hits: list[int]) -> list[tuple[int, float]]:
    matched: list[tuple[int, float]] = []
    for family_id, count in enumerate(hits):
        for _ in range(max(0, int(count))):
            matched.append((family_id, 0.5))
    return matched


def _snapshot_l1(l1: dict[str, Any]) -> dict[str, Any]:
    return {key: l1.get(key) for key in _L1_KEYS if key in l1}


def _energy_vector(l1: dict[str, Any], hits: list[int]) -> list[float]:
    e0 = l1.get("E0")
    if isinstance(e0, list) and e0:
        return [float(x) for x in e0]
    total = float(sum(hits)) or 1.0
    return [float(h) / total for h in hits]


def _perturb_hits(hits: list[int], scale: float) -> list[int]:
    out = [max(0, int(round(h * scale))) for h in hits]
    if out == hits and hits:
        # Guarantee a measurable ε step on the dominant family when rounding collapses.
        dominant = max(range(len(hits)), key=lambda i: hits[i])
        if scale > 1.0:
            out[dominant] = hits[dominant] + 1
        elif scale < 1.0 and hits[dominant] > 0:
            out[dominant] = hits[dominant] - 1
    if sum(out) == 0 and hits:
        dominant = max(range(len(hits)), key=lambda i: hits[i])
        out[dominant] = 1
    return out


def _l1_l2_from_hits(
    hits: list[int],
    *,
    F: int,
    A: int,
    eps: float,
    D: int,
    adjacency: Any,
    total_tokens: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    matched = _matched_from_hits(hits)
    token_count = total_tokens if total_tokens and total_tokens > 0 else max(1, sum(hits))
    l1 = compute_L1(token_count, matched, F=F, A=A, eps=eps)
    l2 = compute_L2(
        l1,
        hits,
        adjacency=adjacency,
        F=F,
        A=A,
        MAX_ALLOWED_DEPTH=D,
        eps=eps,
    )
    return l1, l2


def build_perturbation_series_from_hits(
    base_l1: dict[str, Any],
    hits: list[int],
    *,
    F: int = 288,
    A: int = 12,
    eps: float = 1e-9,
    D: int = 8,
    adjacency: Any = None,
    total_tokens: int | None = None,
    epsilon_magnitude: float | None = None,
) -> dict[str, Any]:
    """Run E(x±ε) as L1/L2 recomputes on scaled hit vectors; return Layer-6 series."""
    from core.layers import build_canonical_stub_adjacency

    adj = adjacency if adjacency is not None else build_canonical_stub_adjacency(F, A)
    eps_mag = float(epsilon_magnitude) if epsilon_magnitude is not None else _epsilon_magnitude()
    plus_hits = _perturb_hits(hits, 1.0 + eps_mag)
    minus_hits = _perturb_hits(hits, max(0.0, 1.0 - eps_mag))
    plus_l1, _plus_l2 = _l1_l2_from_hits(
        plus_hits, F=F, A=A, eps=eps, D=D, adjacency=adj, total_tokens=total_tokens
    )
    minus_l1, _minus_l2 = _l1_l2_from_hits(
        minus_hits, F=F, A=A, eps=eps, D=D, adjacency=adj, total_tokens=total_tokens
    )
    base_output = _energy_vector(base_l1, hits)
    return {
        "epsilon_magnitude": eps_mag,
        "base_output": base_output,
        "base_input_intensity": float(sum(hits)),
        "plus": {
            "l1": _snapshot_l1(plus_l1),
            "output": _energy_vector(plus_l1, plus_hits),
            "input_intensity": float(sum(plus_hits)),
        },
        "minus": {
            "l1": _snapshot_l1(minus_l1),
            "output": _energy_vector(minus_l1, minus_hits),
            "input_intensity": float(sum(minus_hits)),
        },
        "input_vector": base_output,
        "iterate_2_output": base_output,
        "iterate_3_output": base_output,
        "producer": "runtime.services.l6_perturbation_producer",
        "producer_mode": "hit_vector_scale",
    }


def compute_l6_with_optional_producer(
    l1: dict[str, Any],
    l2: dict[str, Any],
    hits: list[int],
    *,
    F: int = 288,
    A: int = 12,
    eps: float = 1e-9,
    D: int = 8,
    adjacency: Any = None,
    total_tokens: int | None = None,
) -> dict[str, Any]:
    """Sealed identity when flag off; measured finite differences when on."""
    if not l6_perturbation_enabled() or not hits:
        return compute_L6(l1, l2, F=F)
    series = build_perturbation_series_from_hits(
        l1,
        hits,
        F=F,
        A=A,
        eps=eps,
        D=D,
        adjacency=adjacency,
        total_tokens=total_tokens,
    )
    return compute_L6(
        l1,
        l2,
        F=F,
        perturbation_enabled=True,
        perturbation_series=series,
    )


def attach_l6_to_engine_result(
    payload: dict[str, Any],
    *,
    family_activation: list[float] | None = None,
    F: int = 288,
    A: int = 12,
) -> dict[str, Any]:
    """Optional `/analyze` meta.layer_6 attach when ``HESPERIA_L6_PERTURBATION=1``."""
    if not l6_perturbation_enabled():
        return payload
    fav = family_activation or []
    if not fav:
        return payload
    from core.layers import build_canonical_stub_adjacency

    # Soft activation → integer hits (preserve relative mass).
    scale = 1000.0
    hits = [max(0, int(round(float(x) * scale))) for x in fav]
    if len(hits) < F:
        hits = hits + [0] * (F - len(hits))
    hits = hits[:F]
    if sum(hits) == 0:
        hits[0] = 1
    adj = build_canonical_stub_adjacency(F, A)
    l1, l2 = _l1_l2_from_hits(hits, F=F, A=A, eps=1e-9, D=8, adjacency=adj)
    l6 = compute_l6_with_optional_producer(
        l1, l2, hits, F=F, A=A, adjacency=adj, total_tokens=sum(hits)
    )
    out = dict(payload)
    meta = dict(out.get("meta") or {})
    meta["layer_6"] = l6
    meta["l6_perturbation"] = {
        "enabled": True,
        "producer": "runtime.services.l6_perturbation_producer",
        "epsilon_magnitude": _epsilon_magnitude(),
    }
    out["meta"] = meta
    return out


def attach_l6_using_raw(
    payload: dict[str, Any],
    raw: dict[str, Any],
    *,
    extract_family_activation: Callable[[dict[str, Any]], list[float]] | None = None,
) -> dict[str, Any]:
    if not l6_perturbation_enabled():
        return payload

    def _default_extract(raw_payload: dict[str, Any]) -> list[float]:
        ms = raw_payload.get("multiscale_signals") or {}
        fav = ms.get("family_activation_vector") or []
        return [float(x) for x in fav]

    extractor = extract_family_activation or _default_extract
    return attach_l6_to_engine_result(payload, family_activation=extractor(raw))
