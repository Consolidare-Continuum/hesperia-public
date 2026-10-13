# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""Baseline semantic trajectory fingerprint T₀ from analyze / invariant bundle."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


def _as_weight_items(raw: Any) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    if isinstance(raw, Mapping):
        for k, v in raw.items():
            try:
                out.append((str(k), float(v)))
            except (TypeError, ValueError):
                continue
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            if isinstance(item, Mapping):
                cid = item.get("id") or item.get("concept_id") or item.get("family_id") or item.get("area_id")
                w = item.get("weight", item.get("activation", item.get("mass", 0.0)))
                if cid is None:
                    continue
                try:
                    out.append((str(cid), float(w)))
                except (TypeError, ValueError):
                    continue
            else:
                out.append((str(item), 1.0))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


def _contradiction_pressure(bundle: Mapping[str, Any]) -> float:
    cr = bundle.get("contradiction_risk") or bundle.get("contradiction") or {}
    if isinstance(cr, Mapping):
        for key in ("contradiction_pressure", "CP", "pressure"):
            if key in cr:
                try:
                    return max(0.0, float(cr[key]))
                except (TypeError, ValueError):
                    pass
    for key in ("contradiction_pressure", "CP"):
        if key in bundle:
            try:
                return max(0.0, float(bundle[key]))
            except (TypeError, ValueError):
                pass
    return 0.0


def _propagation_trace(bundle: Mapping[str, Any]) -> list[str]:
    trace = bundle.get("propagation_trace") or bundle.get("trace") or []
    tags: list[str] = []
    if isinstance(trace, Sequence) and not isinstance(trace, (str, bytes)):
        for step in trace:
            if isinstance(step, Mapping):
                tag = (
                    step.get("rule_tag")
                    or step.get("corridor_id")
                    or step.get("concept_id")
                    or step.get("id")
                )
                if tag is not None:
                    tags.append(str(tag))
            else:
                tags.append(str(step))
    return tags


@dataclass(frozen=True, slots=True)
class SemanticTrajectoryFingerprint:
    """Frozen baseline T₀ — inspection object, not new propagation physics."""

    baseline_id: str
    concepts_activated: tuple[tuple[str, float], ...]
    families_activated: tuple[tuple[str, float], ...]
    areas_activated: tuple[tuple[str, float], ...]
    propagation_trace: tuple[str, ...]
    contradiction_pressure: float
    critical_paths: tuple[str, ...] = field(default_factory=tuple)
    source_keys: tuple[str, ...] = field(default_factory=tuple)

    @property
    def dominant_concept(self) -> str | None:
        return self.concepts_activated[0][0] if self.concepts_activated else None

    @property
    def dominant_family(self) -> str | None:
        return self.families_activated[0][0] if self.families_activated else None

    @property
    def dominant_area(self) -> str | None:
        return self.areas_activated[0][0] if self.areas_activated else None

    def summary(self) -> dict[str, Any]:
        return {
            "top_concepts": [c for c, _ in self.concepts_activated[:5]],
            "dominant_area": self.dominant_area,
            "dominant_family": self.dominant_family,
            "critical_path_count": len(self.critical_paths),
            "contradiction_pressure": self.contradiction_pressure,
        }


def _stable_baseline_id(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest}"


def build_trajectory_fingerprint(
    analyze_bundle: Mapping[str, Any] | None,
    *,
    critical_paths: Sequence[str] | None = None,
    baseline_id: str | None = None,
) -> SemanticTrajectoryFingerprint:
    """Build T₀ from analyze / invariant / sealed-stack-like dict.

    Accepts flat or nested keys (``invariant_activation``, ``sealed_multiscale_stack``).
    """
    bundle: dict[str, Any] = dict(analyze_bundle or {})
    nested_keys = (
        "invariant_activation",
        "sealed_multiscale_stack",
        "activation",
        "engine_result",
    )
    used: list[str] = []
    for key in nested_keys:
        nested = bundle.get(key)
        if isinstance(nested, Mapping):
            used.append(key)
            for nk, nv in nested.items():
                bundle.setdefault(nk, nv)

    concepts = _as_weight_items(
        bundle.get("concepts_activated")
        or bundle.get("concepts")
        or bundle.get("top_concepts")
    )
    families = _as_weight_items(
        bundle.get("families_activated")
        or bundle.get("families")
        or bundle.get("top_families")
    )
    areas = _as_weight_items(
        bundle.get("areas_activated") or bundle.get("areas") or bundle.get("top_areas")
    )
    trace = _propagation_trace(bundle)
    cp = _contradiction_pressure(bundle)
    paths = tuple(str(p) for p in (critical_paths or bundle.get("critical_paths") or ()))

    id_payload = {
        "concepts": concepts[:20],
        "families": families[:20],
        "areas": areas[:20],
        "trace": trace[:40],
        "cp": round(cp, 6),
        "paths": list(paths),
    }
    bid = baseline_id or _stable_baseline_id(id_payload)
    return SemanticTrajectoryFingerprint(
        baseline_id=bid,
        concepts_activated=tuple(concepts),
        families_activated=tuple(families),
        areas_activated=tuple(areas),
        propagation_trace=tuple(trace),
        contradiction_pressure=cp,
        critical_paths=paths,
        source_keys=tuple(used),
    )
