# HESPERIA — Grain-aware public / pack projection layer.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""
Projection / vocabulary remap driven by ``HESPERIA_AREA_MATH_GRAIN``.

- grain **12** (default): keep full 12 areas / 288 families; no pack exclusion
- grain **10**: ten-total packing (drop sealed 10–11 / families 240–287)

Legacy constants ``PUBLIC_AREA_COUNT`` / ``PUBLIC_FAMILY_COUNT`` remain the
**ten-area** sizes for callers that hard-coded the old name; prefer
``active_area_count()`` / ``active_family_count()`` for switch-aware code.
"""

from __future__ import annotations

from typing import Any

from core.projection.area_math_grain import (
    AreaMathGrain,
    active_area_count,
    active_family_count,
    classify_area_math_grain,
    slice_area_vector,
    slice_family_vector,
)
from core.projection.ten_area_module import TEN_AREA_COUNT, TEN_AREA_FAMILY_COUNT
from core.topology import reserve_loader
from core.topology.invariant_catalog import TOTAL_FAMILIES

# Backward-compatible names — ten-area sizes (not necessarily the active grain).
PUBLIC_AREA_COUNT = TEN_AREA_COUNT  # 10
PUBLIC_FAMILY_COUNT = TEN_AREA_FAMILY_COUNT  # 240

KEY_MACRO_DOMAIN_VECTOR = "macro_domain_vector"
KEY_POLICY_FAMILY_COUNTS = "policy_family_counts"
KEY_DOMINANT_MACRO_DOMAIN = "dominant_macro_domain"
KEY_DOMINANT_POLICY_FAMILY = "dominant_policy_family"
KEY_PROPAGATED_MACRO_DOMAIN_VECTOR = "propagated_macro_domain_vector"
KEY_PROPAGATED_POLICY_FAMILY_COUNTS = "propagated_policy_family_counts"
KEY_CORRECTED_MACRO_DOMAIN_VECTOR = "corrected_macro_domain_vector"
KEY_CORRECTED_POLICY_FAMILY_COUNTS = "corrected_policy_family_counts"

KEY_REMAP_CANONICAL = {
    "stability": "consistency_profile",
    "pipeline": "execution_flow",
}


def _grain(explicit: AreaMathGrain | int | None = None) -> AreaMathGrain:
    if explicit is None:
        return classify_area_math_grain()
    return classify_area_math_grain(explicit=explicit)


def filter_reserved_structures(
    area_indices: list[int] | None = None,
    family_indices: list[int] | None = None,
    side_ids: list[int] | None = None,
    *,
    grain: AreaMathGrain | int | None = None,
) -> dict[str, Any]:
    """Filter pack-excluded indices under the active (or explicit) grain."""
    g = _grain(grain)
    out: dict[str, Any] = {
        "area_indices": [],
        "family_indices": [],
        "side_ids": [],
    }
    if area_indices is not None:
        out["area_indices"] = [
            a for a in area_indices if not reserve_loader.is_reserved_area(a, grain=g)
        ]
    if family_indices is not None:
        out["family_indices"] = [
            f for f in family_indices if not reserve_loader.is_reserved_family(f, grain=g)
        ]
    if side_ids is not None:
        out["side_ids"] = [
            s for s in side_ids if not reserve_loader.is_reserved_side_id(s, grain=g)
        ]
    return out


def project_public_areas(
    internal_area_vector: list[float] | None = None,
    internal_area_indices: list[int] | None = None,
    *,
    grain: AreaMathGrain | int | None = None,
) -> dict[str, Any]:
    """Project area vector/indices to the active grain length (10 or 12)."""
    g = _grain(grain)
    n = active_area_count(g)
    result: dict[str, Any] = {"area_math_grain": g}
    if internal_area_vector is not None and len(internal_area_vector) >= min(10, n):
        result[KEY_MACRO_DOMAIN_VECTOR] = slice_area_vector(internal_area_vector, grain=g)
    if internal_area_indices is not None:
        result["macro_domain_indices"] = [
            i
            for i in internal_area_indices
            if not reserve_loader.is_reserved_area(i, grain=g) and 0 <= i < n
        ]
    return result


def project_public_families(
    internal_family_counts: list[float] | list[int] | None = None,
    internal_family_indices: list[int] | None = None,
    *,
    grain: AreaMathGrain | int | None = None,
) -> dict[str, Any]:
    """Project family counts/indices to the active grain family count (240 or 288)."""
    g = _grain(grain)
    n = active_family_count(g)
    result: dict[str, Any] = {"area_math_grain": g}
    if internal_family_counts is not None and len(internal_family_counts) >= min(PUBLIC_FAMILY_COUNT, n):
        result[KEY_POLICY_FAMILY_COUNTS] = slice_family_vector(internal_family_counts, grain=g)
    if internal_family_indices is not None:
        result["policy_family_indices"] = [
            i
            for i in internal_family_indices
            if not reserve_loader.is_reserved_family(i, grain=g) and 0 <= i < TOTAL_FAMILIES
            and i < n
        ]
    return result


def project_public_metrics(
    internal_metrics: dict[str, Any],
    *,
    grain: AreaMathGrain | int | None = None,
) -> dict[str, Any]:
    """Remap internal metrics to public vocabulary under the active grain."""
    g = _grain(grain)
    n_areas = active_area_count(g)
    n_fams = active_family_count(g)
    out: dict[str, Any] = {"area_math_grain": g}

    if "area_vector" in internal_metrics:
        av = internal_metrics["area_vector"]
        if isinstance(av, (list, tuple)) and len(av) >= min(10, n_areas):
            out[KEY_MACRO_DOMAIN_VECTOR] = slice_area_vector(av, grain=g)
    if "propagated_area_vector" in internal_metrics:
        av = internal_metrics["propagated_area_vector"]
        if isinstance(av, (list, tuple)) and len(av) >= min(10, n_areas):
            out[KEY_PROPAGATED_MACRO_DOMAIN_VECTOR] = slice_area_vector(av, grain=g)
    if "corrected_area_vector" in internal_metrics:
        av = internal_metrics["corrected_area_vector"]
        if isinstance(av, (list, tuple)) and len(av) >= min(10, n_areas):
            out[KEY_CORRECTED_MACRO_DOMAIN_VECTOR] = slice_area_vector(av, grain=g)

    if "family_counts" in internal_metrics:
        fc = internal_metrics["family_counts"]
        if isinstance(fc, (list, tuple)) and len(fc) >= min(PUBLIC_FAMILY_COUNT, n_fams):
            out[KEY_POLICY_FAMILY_COUNTS] = slice_family_vector(fc, grain=g)
    if "propagated_family_counts" in internal_metrics:
        fc = internal_metrics["propagated_family_counts"]
        if isinstance(fc, (list, tuple)) and len(fc) >= min(PUBLIC_FAMILY_COUNT, n_fams):
            out[KEY_PROPAGATED_POLICY_FAMILY_COUNTS] = slice_family_vector(fc, grain=g)
    if "corrected_family_counts" in internal_metrics:
        fc = internal_metrics["corrected_family_counts"]
        if isinstance(fc, (list, tuple)) and len(fc) >= min(PUBLIC_FAMILY_COUNT, n_fams):
            out[KEY_CORRECTED_POLICY_FAMILY_COUNTS] = slice_family_vector(fc, grain=g)

    dominant_area = internal_metrics.get("dominant_area") or internal_metrics.get("DOMINANT_AREA_ID")
    if dominant_area is not None:
        a = int(dominant_area)
        if not reserve_loader.is_reserved_area(a, grain=g) and 0 <= a < n_areas:
            out[KEY_DOMINANT_MACRO_DOMAIN] = a
    dominant_family = internal_metrics.get("dominant_family") or internal_metrics.get("DOMINANT_FAMILY_ID")
    if dominant_family is not None:
        f = int(dominant_family)
        if not reserve_loader.is_reserved_family(f, grain=g) and 0 <= f < n_fams:
            out[KEY_DOMINANT_POLICY_FAMILY] = f

    safe_keys = {
        "entropy", "coverage", "tension", "loopability", "governance",
        "constraint_status", "structural_recurrence", "resistance_index",
        "confidence", "trust_tier", "contradiction", "divergence",
        "structural_focus", "evidence_count", "run_version", "result_hash",
    }
    for k, v in internal_metrics.items():
        if k in safe_keys or (k not in out and not _is_internal_revealing_key(k)):
            if k not in (
                "area_vector", "family_counts", "propagated_area_vector", "propagated_family_counts",
                "corrected_area_vector", "corrected_family_counts",
                "dominant_area", "dominant_family", "DOMINANT_AREA_ID", "DOMINANT_FAMILY_ID",
            ):
                out[k] = v
    if "governance" in out and "constraint_status" not in out:
        out["constraint_status"] = out["governance"]
    if "loopability" in out and "structural_recurrence" not in out:
        out["structural_recurrence"] = out["loopability"]
    if "obstacle_score" in out and "resistance_index" not in out:
        out["resistance_index"] = out["obstacle_score"]
    return out


def _is_internal_revealing_key(key: str) -> bool:
    revealing = (
        "side_id", "hex", "hexagon", "sphere", "topology", "adjacency",
        "area_sequence", "family_sequence", "area_id", "family_id",
        "AREA_", "FAMILY_", "layer_", "bridge",
    )
    return any(r in key.lower() for r in revealing)


def sanitize_public_trace(
    trace: dict[str, Any] | list[Any],
    *,
    grain: AreaMathGrain | int | None = None,
) -> dict[str, Any] | list[Any]:
    """Sanitize for emission under the active grain (12 keeps CREATION/DECEIT)."""
    g = _grain(grain)
    if isinstance(trace, list):
        return [
            sanitize_public_trace(item, grain=g)
            for item in trace
            if _trace_item_safe(item, grain=g)
        ]
    if not isinstance(trace, dict):
        return trace
    n_areas = active_area_count(g)
    n_fams = active_family_count(g)
    out: dict[str, Any] = {}
    for k, v in trace.items():
        if _is_internal_revealing_key(k):
            continue
        if k == "execution_time_ms":
            continue
        if k in (
            "area_vector",
            "family_counts",
            "propagated_area_vector",
            "propagated_family_counts",
            "corrected_area_vector",
            "corrected_family_counts",
        ) and isinstance(v, (list, tuple)):
            if "area" in k:
                key = (
                    KEY_MACRO_DOMAIN_VECTOR
                    if k == "area_vector"
                    else (
                        KEY_PROPAGATED_MACRO_DOMAIN_VECTOR
                        if k == "propagated_area_vector"
                        else KEY_CORRECTED_MACRO_DOMAIN_VECTOR
                    )
                )
                out[key] = slice_area_vector(v, grain=g)
            else:
                key = (
                    KEY_POLICY_FAMILY_COUNTS
                    if k == "family_counts"
                    else (
                        KEY_PROPAGATED_POLICY_FAMILY_COUNTS
                        if k == "propagated_family_counts"
                        else KEY_CORRECTED_POLICY_FAMILY_COUNTS
                    )
                )
                out[key] = slice_family_vector(v, grain=g)
            continue
        if k in ("dominant_area", "dominant_family", "DOMINANT_AREA_ID", "DOMINANT_FAMILY_ID"):
            idx = int(v) if v is not None else None
            if idx is not None:
                if "area" in k and not reserve_loader.is_reserved_area(idx, grain=g) and idx < n_areas:
                    out[KEY_DOMINANT_MACRO_DOMAIN] = idx
                elif "family" in k and not reserve_loader.is_reserved_family(idx, grain=g) and idx < n_fams:
                    out[KEY_DOMINANT_POLICY_FAMILY] = idx
            continue
        out_key = KEY_REMAP_CANONICAL.get(k, k)
        out[out_key] = sanitize_public_trace(v, grain=g) if isinstance(v, (dict, list)) else v
    if "area_math_grain" not in out:
        out["area_math_grain"] = g
    return out


def apply_public_projection(
    payload: dict[str, Any],
    *,
    grain: AreaMathGrain | int | None = None,
) -> dict[str, Any]:
    """Grain-aware sanitize gate (default grain 12; set env/arg for 10)."""
    return sanitize_public_trace(payload, grain=grain)  # type: ignore[return-value]


def _trace_item_safe(item: Any, *, grain: AreaMathGrain) -> bool:
    if isinstance(item, dict):
        sid = item.get("side_id")
        if sid is not None:
            try:
                if reserve_loader.is_reserved_side_id(int(sid), grain=grain):
                    return False
            except (TypeError, ValueError):
                pass
        fid = item.get("family_id")
        if fid is not None:
            try:
                if reserve_loader.is_reserved_family(int(fid), grain=grain):
                    return False
            except (TypeError, ValueError):
                pass
        aid = item.get("area_id")
        if aid is not None:
            try:
                if reserve_loader.is_reserved_area(int(aid), grain=grain):
                    return False
            except (TypeError, ValueError):
                pass
    return True
