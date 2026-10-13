# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""IPoV — Interior Point of World View. Spec: SPEC-GRACE-HESPERIA-INTERIOR-POINT-OF-WORLD-VIEW.md

Sibling to sphere/topology/gtp/ — both are "where is the reader positioned in the
concept sphere" concerns. Drained from Tersagor's vendored tersagor_agent/hesperia/geometry/
2026-08-04 (never previously built in Hesperia itself, despite HES-61-07 scaffolding it
as Hesperia-side work — same situation as core/domain/ksi/).
"""

from .anchor_map import ANCHOR_MAP, AREA_RING, AnchorMap, GeodesicConstants, Vec3
from .powv import InteriorPointOfWorldView, PoWVState, compute_powv_step
from .schemas import InteriorPovBlock
from .session_export import powv_to_pov_block
from .surface_events import EventBatch, SurfaceEvent, SurfaceEventType

__all__ = [
    "ANCHOR_MAP",
    "AREA_RING",
    "AnchorMap",
    "EventBatch",
    "GeodesicConstants",
    "InteriorPointOfWorldView",
    "InteriorPovBlock",
    "PoWVState",
    "SurfaceEvent",
    "SurfaceEventType",
    "Vec3",
    "compute_powv_step",
    "powv_to_pov_block",
]
