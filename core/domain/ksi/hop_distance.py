# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""D_e hop distance from propagation_trace (KSI spec section 4)."""
from __future__ import annotations

from typing import Any, Mapping


def hop_distance_from_trace(
    concept_i: str,
    concept_j: str,
    propagation_trace: list[Mapping[str, Any]] | None,
) -> int:
    if not propagation_trace:
        return 1
    index = {str(step.get("concept_id", "")): i for i, step in enumerate(propagation_trace)}
    if concept_i not in index or concept_j not in index:
        return max(1, abs(len(propagation_trace)))
    return max(1, abs(index[concept_j] - index[concept_i]))
