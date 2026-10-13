# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""Extract critical paths Π* from baseline trajectory T₀."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from sphere.kam.bounds import KamBounds, load_kam_bounds
from sphere.kam.trajectory_fingerprint import SemanticTrajectoryFingerprint


def _corridor_edges(bundle: Mapping[str, Any]) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    corridors = bundle.get("propagation_corridors") or bundle.get("corridors") or {}
    edges = None
    if isinstance(corridors, Mapping):
        edges = corridors.get("corridor_edges") or corridors.get("edges")
    elif isinstance(corridors, Sequence) and not isinstance(corridors, (str, bytes)):
        edges = corridors
    if edges is None:
        edges = bundle.get("corridor_edges") or []
    if isinstance(edges, Mapping):
        for eid, mass in edges.items():
            try:
                out.append((str(eid), float(mass)))
            except (TypeError, ValueError):
                continue
    elif isinstance(edges, Sequence) and not isinstance(edges, (str, bytes)):
        for item in edges:
            if isinstance(item, Mapping):
                eid = item.get("id") or item.get("edge") or item.get("corridor_id")
                mass = item.get("mass", item.get("weight", item.get("activation", 0.0)))
                if eid is None:
                    src = item.get("source") or item.get("from")
                    tgt = item.get("target") or item.get("to")
                    if src is not None and tgt is not None:
                        eid = f"{src}->{tgt}"
                if eid is None:
                    continue
                try:
                    out.append((str(eid), float(mass)))
                except (TypeError, ValueError):
                    continue
            else:
                out.append((str(item), 1.0))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


def extract_critical_paths(
    fingerprint: SemanticTrajectoryFingerprint,
    analyze_bundle: Mapping[str, Any] | None = None,
    *,
    bounds: KamBounds | None = None,
    top_k: int = 8,
) -> tuple[str, ...]:
    """Build Π* from corridor edges / dominant area–family chain / heavy trace.

    Paths with mass ≥ ``τ_crit`` (or top-k when masses absent) become critical.
    Empty Π* is a valid outcome → insufficient_baseline downstream.
    """
    b = bounds or load_kam_bounds()
    bundle = dict(analyze_bundle or {})
    paths: list[str] = []

    if fingerprint.critical_paths:
        return tuple(fingerprint.critical_paths)

    for eid, mass in _corridor_edges(bundle):
        if mass >= b.tau_crit:
            paths.append(f"corridor:{eid}")

    if fingerprint.dominant_area and fingerprint.dominant_family:
        paths.append(
            f"area_family:{fingerprint.dominant_area}->{fingerprint.dominant_family}"
        )
    if fingerprint.dominant_area:
        paths.append(f"within_area:{fingerprint.dominant_area}")

    for tag in fingerprint.propagation_trace:
        # Trace segments without explicit mass: include as soft critical if top-k room.
        seg = f"trace:{tag}"
        if seg not in paths:
            paths.append(seg)

    # Deduplicate preserving order; cap top_k.
    seen: set[str] = set()
    ordered: list[str] = []
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        ordered.append(p)
        if len(ordered) >= top_k:
            break
    return tuple(ordered)


def with_critical_paths(
    fingerprint: SemanticTrajectoryFingerprint,
    paths: Sequence[str],
) -> SemanticTrajectoryFingerprint:
    """Return a copy of fingerprint with Π* attached."""
    return SemanticTrajectoryFingerprint(
        baseline_id=fingerprint.baseline_id,
        concepts_activated=fingerprint.concepts_activated,
        families_activated=fingerprint.families_activated,
        areas_activated=fingerprint.areas_activated,
        propagation_trace=fingerprint.propagation_trace,
        contradiction_pressure=fingerprint.contradiction_pressure,
        critical_paths=tuple(str(p) for p in paths),
        source_keys=fingerprint.source_keys,
    )
