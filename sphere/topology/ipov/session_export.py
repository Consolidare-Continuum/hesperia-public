# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
IPoV-06 — Session/iteration PoWV export and Inspector read-only strip.

Spec: SPEC-GRACE-HESPERIA-INTERIOR-POINT-OF-WORLD-VIEW.md §5.2

Converts InteriorPointOfWorldView into the compact InteriorPovBlock
suitable for embedding in the context_rag packet or iteration bundle.
Also provides a session accumulator for multi-step exports.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .powv import InteriorPointOfWorldView, PoWVState
from .schemas import InteriorPovBlock


def powv_to_pov_block(snapshot: InteriorPointOfWorldView) -> InteriorPovBlock:
    """
    Convert a full InteriorPointOfWorldView snapshot to the compact
    InteriorPovBlock for embedding in context packets / iteration bundles.
    Picks top-3 nearest areas by d_relative.
    """
    r = snapshot.r()
    r_norm = math.sqrt(r[0] ** 2 + r[1] ** 2 + r[2] ** 2)

    # Top-3 nearest areas (smallest d = closest)
    sorted_areas = sorted(snapshot.area_distances, key=lambda e: e.d)[:3]
    nearest_areas = {e.area_id: round(e.d_relative, 6) for e in sorted_areas}

    return InteriorPovBlock(
        schema_name="interior_point_of_world_view_v1",
        step=snapshot.step,
        point_zero=snapshot.point_zero,
        r_x=round(r[0], 8),
        r_y=round(r[1], 8),
        r_z=round(r[2], 8),
        r_norm=round(r_norm, 8),
        nearest_areas=nearest_areas,
        barycentric_areas=[round(w, 6) for w in snapshot.barycentric_areas],
        update_mode=snapshot.provenance.update_mode,
    )


@dataclass
class PoWVSessionExport:
    """
    Accumulates PoWV snapshots across a session for Inspector read-only strip.
    IPoV-06.
    """

    steps: list[InteriorPovBlock] = field(default_factory=list)

    def record(self, snapshot: InteriorPointOfWorldView) -> None:
        self.steps.append(powv_to_pov_block(snapshot))

    def latest(self) -> InteriorPovBlock | None:
        return self.steps[-1] if self.steps else None

    def to_inspector_strip(self) -> list[dict]:
        """Return read-only strip suitable for Inspector UI (list of dicts)."""
        return [s.model_dump() for s in self.steps]

    def reset(self) -> None:
        self.steps.clear()
