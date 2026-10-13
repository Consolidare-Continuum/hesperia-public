# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.
#
# MOVED 2026-07-31: the real implementation now lives in core.math.graph_matrix_builders —
# this module is a first-class dynamics extension of core, not the owner of this math.
# Re-exported for backward compatibility; existing imports from this path keep working.

from __future__ import annotations

from core.math.graph_matrix_builders import (
    build_contradiction_matrix,
    build_family_adjacency_matrix,
    build_family_index,
    build_resistance_vector,
)

__all__ = [
    "build_family_index",
    "build_family_adjacency_matrix",
    "build_contradiction_matrix",
    "build_resistance_vector",
]
