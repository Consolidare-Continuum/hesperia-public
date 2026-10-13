# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KsiConceptMetrics(BaseModel):
    expected: float = 0.0
    observed: float = 0.0
    residual: float = 0.0
    incident: str | None = None


class KsiBundleBlock(BaseModel):
    """KSI bundle extension attached to HybridRetrieveOutput (KSI spec §15)."""

    version: str = "0.1"
    concepts: dict[str, KsiConceptMetrics] = Field(default_factory=dict)
    areas: dict[str, KsiConceptMetrics] = Field(default_factory=dict)
    incidents: list[dict[str, Any]] = Field(default_factory=list)
    missing_bridges: list[dict[str, Any]] = Field(default_factory=list)
    phi_trace: dict[str, Any] | None = None


def empty_ksi_block() -> KsiBundleBlock:
    """Deterministic stub when live propagation / engine trace is unavailable."""
    return KsiBundleBlock(version="0.1")
