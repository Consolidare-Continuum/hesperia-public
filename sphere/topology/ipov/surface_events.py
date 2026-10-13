# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
IPoV-04 — Surface event types and batch.

Spec: SPEC-GRACE-HESPERIA-INTERIOR-POINT-OF-WORLD-VIEW.md §4.1

Surface events translate traversal/guard/shadow engine outputs into
PoWV update inputs.  This module defines the data shapes only;
wiring to the actual traversal engine is done at integration time.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .anchor_map import ANCHOR_MAP, AREA_RING, AnchorMap, Vec3


def _geodesic_distance_on_sphere(a: Vec3, b: Vec3) -> float:
    dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    dot = max(-1.0, min(1.0, dot))
    return math.acos(dot)


def _compute_path_metric(edges: list[dict[str, Any]]) -> dict[str, Any]:
    """24_SPEC §5 path action — local copy for SurfaceEventBatch payloads."""
    total = 0.0
    layers_seen: list[str] = []
    for edge in edges:
        layer = str(edge.get("layer", "hex_graph"))
        if layer == "area_sphere":
            length = float(edge.get("geodesic_distance", 0.0))
        elif layer == "hex_graph":
            length = 1.0
        else:
            length = float(edge.get("cost", 0.0))
        total += length
        if layer not in layers_seen:
            layers_seen.append(layer)
    return {
        "path_metric_cost": round(total, 6),
        "path_metric_layers": layers_seen,
        "path_action_version": "0.1",
    }


class SurfaceEventType(str, Enum):
    TRAVERSAL = "traversal"        # Normal step on surface
    BORDER_PASSING = "border"      # Area/family boundary crossing
    GUARD_BLOCK = "guard_block"    # Guard/Sigma/Gamma blocked traversal
    GUARD_PASS = "guard_pass"      # Guard allowed traversal
    SHADOW = "shadow"              # Shadow perturbation applied
    ACTIVATION = "activation"      # Explicit activation slice update


@dataclass
class SurfaceEvent:
    """
    One surface event record.
    Spec §4.1 — produced by traversal engine, consumed by PoWV updater.
    """

    event_type: SurfaceEventType
    step: int

    area_id: str = ""
    global_id: int = -1          # 0-based global family index (-1 = unknown)
    border_passings: int = 0
    guard_events: list[str] = field(default_factory=list)
    shadow_delta: float = 0.0    # perturbation magnitude when event_type == SHADOW
    activation_slice: dict[str, float] = field(default_factory=dict)  # area_id → weight


@dataclass
class EventBatch:
    """
    Batch of surface events for one PoWV update cycle.
    Translates events into (anchor_direction, weight) pairs for compute_powv_step().
    """

    events: list[SurfaceEvent] = field(default_factory=list)
    anchor_map: AnchorMap | None = None

    def to_event_vectors(self) -> list[tuple[Vec3, float]]:
        """
        Convert event batch to list of (anchor_direction, weight) pairs.

        Weights:
        - TRAVERSAL: +1.0 pull toward visited area/family
        - BORDER_PASSING: +0.5 per border crossed (topic shift)
        - GUARD_BLOCK: -0.3 per event (inward/penalty pull)
        - GUARD_PASS: +0.2 (governance alignment boost)
        - SHADOW: small perturbation via shadow_delta magnitude
        - ACTIVATION: area weights as-is
        """
        am = self.anchor_map or ANCHOR_MAP
        vectors: list[tuple[Vec3, float]] = []

        for ev in self.events:
            if ev.event_type == SurfaceEventType.TRAVERSAL and ev.area_id in AREA_RING:
                s = am.area_direction(ev.area_id)
                vectors.append((s, 1.0))
                # Also pull toward family if known
                if ev.global_id >= 0:
                    ai, fi = am.area_family_from_global(ev.global_id)
                    s_fam = am.family_directions[ai][fi]
                    vectors.append((s_fam, 0.5))

            elif ev.event_type == SurfaceEventType.BORDER_PASSING and ev.area_id in AREA_RING:
                s = am.area_direction(ev.area_id)
                vectors.append((s, 0.5 * max(1, ev.border_passings)))

            elif ev.event_type == SurfaceEventType.GUARD_BLOCK and ev.area_id in AREA_RING:
                s = am.area_direction(ev.area_id)
                vectors.append((s, -0.3 * len(ev.guard_events or [1])))

            elif ev.event_type == SurfaceEventType.GUARD_PASS and ev.area_id in AREA_RING:
                s = am.area_direction(ev.area_id)
                vectors.append((s, 0.2))

            elif ev.event_type == SurfaceEventType.SHADOW:
                # Shadow applies a small inward perturbation proportional to shadow_delta
                if ev.area_id in AREA_RING:
                    s = am.area_direction(ev.area_id)
                    vectors.append((s, ev.shadow_delta * 0.1))

            elif ev.event_type == SurfaceEventType.ACTIVATION:
                for area_id, weight in ev.activation_slice.items():
                    if area_id in AREA_RING:
                        s = am.area_direction(area_id)
                        vectors.append((s, weight))

        return vectors

    def to_path_edges(self) -> list[dict[str, Any]]:
        """Build sealed path edges for 24_SPEC §5 path_metric_cost (METRIC-25)."""
        am = self.anchor_map or ANCHOR_MAP
        edges: list[dict[str, Any]] = []
        prev_area: str | None = None
        prev_gid: int | None = None

        for ev in self.events:
            if ev.event_type not in (
                SurfaceEventType.TRAVERSAL,
                SurfaceEventType.BORDER_PASSING,
            ):
                continue
            if ev.area_id not in AREA_RING:
                continue

            if prev_area is not None and ev.area_id != prev_area:
                d1 = am.area_direction(prev_area)
                d2 = am.area_direction(ev.area_id)
                edges.append(
                    {
                        "layer": "area_sphere",
                        "from_area_id": prev_area,
                        "to_area_id": ev.area_id,
                        "geodesic_distance": _geodesic_distance_on_sphere(d1, d2),
                    }
                )

            if (
                prev_gid is not None
                and ev.global_id >= 0
                and prev_gid >= 0
                and ev.global_id != prev_gid
            ):
                edges.append(
                    {
                        "layer": "hex_graph",
                        "from_global_id": prev_gid,
                        "to_global_id": ev.global_id,
                    }
                )

            prev_area = ev.area_id
            if ev.global_id >= 0:
                prev_gid = ev.global_id

            if ev.event_type == SurfaceEventType.BORDER_PASSING:
                for _ in range(max(0, ev.border_passings - 1)):
                    edges.append(
                        {
                            "layer": "hex_graph",
                            "from_area_id": ev.area_id,
                            "to_area_id": ev.area_id,
                        }
                    )

        return edges

    def to_traversal_payload(self) -> dict[str, Any]:
        """Serialize batch with path_metric_cost for traversal / matrix_run consumers."""
        edges = self.to_path_edges()
        payload: dict[str, Any] = {
            "surface_event_batch": True,
            "event_count": len(self.events),
            "events": [
                {
                    "event_type": ev.event_type.value,
                    "step": ev.step,
                    "area_id": ev.area_id,
                    "global_id": ev.global_id,
                    "border_passings": ev.border_passings,
                }
                for ev in self.events
            ],
        }
        if edges:
            payload.update(_compute_path_metric(edges))
        else:
            payload.update(
                {
                    "path_metric_cost": 0.0,
                    "path_metric_layers": [],
                    "path_action_version": "0.1",
                }
            )
        return payload


# Spec alias (24_SPEC SurfaceEventBatch)
SurfaceEventBatch = EventBatch
