# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""IPoV-05 — interior_pov output block schema. Spec: SPEC-GRACE-HESPERIA-INTERIOR-POINT-OF-WORLD-VIEW.md §5.2"""

from __future__ import annotations

from pydantic import BaseModel, Field


class InteriorPovBlock(BaseModel):
    """
    IPoV-05 — optional interior_pov block in context_rag / iteration bundle.
    Spec: SPEC-GRACE-HESPERIA-INTERIOR-POINT-OF-WORLD-VIEW.md §5.2
    """

    schema_name: str = "interior_point_of_world_view_v1"
    step: int = 0
    point_zero: bool = True
    r_x: float = 0.0
    r_y: float = 0.0
    r_z: float = 0.0
    r_norm: float = 0.0
    # Top-3 closest areas by distance (area_id -> d_relative)
    nearest_areas: dict[str, float] = Field(default_factory=dict)
    # Barycentric area weights (12 values)
    barycentric_areas: list[float] = Field(default_factory=list)
    update_mode: str = "point_zero"
