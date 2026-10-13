# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

# Math infrastructure: deterministic numerical primitives only.
# Sphere layers must import from core.math; they must not implement math.

from core.math.entropy_metrics import compute_entropy, compute_normalized_entropy
from core.math.stability_metrics import (
    compute_stability_index,
    compute_structural_tension,
)
from core.math.curvature_metrics import compute_curvature, compute_jump_rate
from core.math.transition_matrix import (
    compute_transition_matrix,
    compute_transition_probabilities,
)
from core.math.sequence_utils import build_trajectory, compress_trajectory
from core.math.sequence_metrics import compute_loopability
from core.math.vector_ops import (
    detect_dominant_area,
    detect_dominant_family,
    detect_family_peaks,
)
from core.math.coverage import compute_family_coverage, compute_area_coverage

__all__ = [
    "compute_entropy",
    "compute_normalized_entropy",
    "compute_stability_index",
    "compute_structural_tension",
    "compute_curvature",
    "compute_jump_rate",
    "compute_transition_matrix",
    "compute_transition_probabilities",
    "build_trajectory",
    "compress_trajectory",
    "compute_loopability",
    "detect_dominant_area",
    "detect_dominant_family",
    "detect_family_peaks",
    "compute_family_coverage",
    "compute_area_coverage",
]
