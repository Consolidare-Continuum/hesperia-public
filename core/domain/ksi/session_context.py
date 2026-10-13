# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""Read-only IPoV/GTP hooks for KSI session context (v0.1 stubs)."""
from __future__ import annotations

from typing import Any, Mapping


def ipov_surface_events_stub(interior_pov: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not interior_pov:
        return []
    return [{"source": "ipov", "r": interior_pov.get("r"), "step_count": len(interior_pov.get("steps") or [])}]


def gtp_psi_scalar_stub(gtp_coherence: Mapping[str, Any] | None) -> float | None:
    if not gtp_coherence:
        return None
    psi = gtp_coherence.get("psi") or gtp_coherence.get("coherence_psi")
    return float(psi) if psi is not None else None
