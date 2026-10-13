# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Structural tension — orchestration only; math lives in core.math.
"""

from __future__ import annotations

from core.math.stability_metrics import compute_structural_tension
from core.topology.invariant_catalog import AREAS as TOTAL_AREAS

__all__ = ["compute_structural_tension", "TOTAL_AREAS"]
