# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA layer execution contract.
All layers (L1–L9) consume LayerInput and produce LayerOutput.
Single public entry point per layer: run(input_data: LayerInput) -> LayerOutput.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class LayerInput:
    """Canonical input_data for every layer. Metadata carries execution_flow input_context and prior layer outputs."""

    text: str
    tokens: list[str]
    metadata: Dict[str, Any]


@dataclass
class LayerOutput:
    """Canonical output from every layer. Summary is layer-specific; diagnostics for orchestration and performance."""

    layer_id: int
    result: Dict[str, Any]  # compatibility field name; contains per-layer summary values
    diagnostics: Dict[str, Any]


