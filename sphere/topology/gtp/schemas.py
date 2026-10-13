# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
GTP-02 — gtp_v0_1 Pydantic schemas and fixture.

Spec: HESPERIA-FORMALIZATION-GENERAL-THOUGHT-PROPAGATION-v0_1.md §13
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class GtpSideSpecSchema(BaseModel):
    """One side spec entry for gtp_v0_1 registry. Spec §13."""

    side_id: int
    logical: str
    semantic_ro: str
    semantic_en: str


class GtpSemanticReserved(BaseModel):
    id: str
    semantic_ro: str
    semantic_en: str
    stateless: bool
    side_id: Optional[int] = None


class GtpCoherenceSummary(BaseModel):
    psi_scalar: float = 0.0
    psi_abs: float = 0.0
    psi_align: float = 0.0
    vector_dim: int = 300


class GtpV0_1(BaseModel):
    """
    gtp_v0_1 registry object — frozen operator tables + current state.
    Spec §13.
    """

    hex_rotation: int = 0
    side_specs: list[GtpSideSpecSchema] = Field(default_factory=list)
    semantic_reserved: list[GtpSemanticReserved] = Field(default_factory=list)
    point_zero_delta: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    coherence: GtpCoherenceSummary = Field(default_factory=GtpCoherenceSummary)
    thought_imprint: list[dict[str, Any]] = Field(default_factory=list)
    imprint_difference: dict[str, Any] = Field(default_factory=dict)


class GtpCoherenceBlock(BaseModel):
    """
    GTP-07 — optional GTP coherence block attached to a retrieve output or packet.
    Spec: HESPERIA-FORMALIZATION-GENERAL-THOUGHT-PROPAGATION-v0_1.md §13
    """

    schema_name: str = "gtp_iteration_bundle_v0_1"
    psi_scalar: float = 0.0
    psi_abs: float = 0.0
    psi_align: float = 0.0
    chosen_area_id: str = ""
    chosen_global_id: int = -1
    gtpa_score: float = 0.0
    dominant_shift: bool = False


class GtpIterationBundle(BaseModel):
    """
    GTP-07 — optional GTP block attached to an iteration bundle / coherence_hints.
    Wire into HybridRetrieveOutput.gtp_coherence or context_rag packet.
    """

    schema_name: str = "gtp_iteration_bundle_v0_1"
    step: int = 0

    # Coherence field summary (from CoherenceField)
    psi_scalar: float = 0.0
    psi_abs: float = 0.0
    psi_align: float = 0.0
    psi_ent: float = 0.0
    area_projections: list[float] = Field(default_factory=lambda: [0.0] * 12)

    # GTPA result
    chosen_area_id: str = ""
    chosen_global_id: int = -1
    chosen_hex_index: int = 0
    chosen_hex_rotation: int = 0
    chosen_exit_side: int = 0
    gtpa_score: float = 0.0

    # Imprint difference summary
    score_delta: float = 0.0
    dominant_shift: bool = False
    new_logical: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Frozen fixture — GTP_FIXTURE
# ---------------------------------------------------------------------------

GTP_FIXTURE = GtpV0_1(
    hex_rotation=0,
    side_specs=[
        GtpSideSpecSchema(side_id=0, logical="INCLUDES",     semantic_ro="cu",      semantic_en="with"),
        GtpSideSpecSchema(side_id=1, logical="NOT_INCLUDES", semantic_ro="din",     semantic_en="from"),
        GtpSideSpecSchema(side_id=2, logical="SUBSUMES",     semantic_ro="la",      semantic_en="at"),
        GtpSideSpecSchema(side_id=3, logical="OVERLAPS",     semantic_ro="spre",    semantic_en="toward"),
        GtpSideSpecSchema(side_id=4, logical="DISJOINT",     semantic_ro="dupa",    semantic_en="after"),
        GtpSideSpecSchema(side_id=5, logical="EQUIVALENT",   semantic_ro="pentru",  semantic_en="for"),
    ],
    semantic_reserved=[
        GtpSemanticReserved(id="FARA", semantic_ro="fara", semantic_en="without", stateless=True, side_id=None),
    ],
    point_zero_delta={"x": 0.0, "y": 0.0, "z": 0.0},
    coherence=GtpCoherenceSummary(psi_scalar=0.0, psi_abs=0.0, psi_align=0.0, vector_dim=300),
    thought_imprint=[],
    imprint_difference={},
)
