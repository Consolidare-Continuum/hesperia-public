# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

# HESPERIA layer stack L1–L9 (Engine Dynamics 0.5.0; specs 34–42; L1 N1 profile).
from .defaults import load_defaults
from .layer_1 import compute_L1
from .layer_2 import compute_L2, build_canonical_stub_adjacency
from .layer_3 import compute_L3
from .layer_4 import compute_L4
from .layer_5 import compute_L5
from .layer_6 import compute_L6
from .layer_7 import compute_L7
from .layer_8 import compute_L8
from .layer_9 import compute_L9
from .structure_profile import (
    StructureProfile,
    load_structure_profile,
    validate_profile,
    profile_checksum,
    require_canonical_taxonomy,
    PRIMARY_AXIS_VALUES,
    STRICTNESS_LEVEL_VALUES,
)
__all__ = [
    "load_defaults", "compute_L1", "compute_L2", "build_canonical_stub_adjacency",
    "compute_L3", "compute_L4", "compute_L5", "compute_L6", "compute_L7", "compute_L8", "compute_L9",
    "StructureProfile", "load_structure_profile", "validate_profile", "profile_checksum",
    "require_canonical_taxonomy", "PRIMARY_AXIS_VALUES", "STRICTNESS_LEVEL_VALUES",
]
