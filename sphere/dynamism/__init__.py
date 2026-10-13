# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

# Layer-6 Dynamism Layer: trajectory, transition matrix, curvature, jump rate, stability.
from sphere.dynamism.dynamism_engine import compute_dynamism
from sphere.dynamism.trajectory import build_trajectory, compress_trajectory
from sphere.dynamism.transition_matrix import (
    compute_transition_matrix,
    compute_transition_probabilities,
)
from sphere.dynamism.curvature import compute_curvature
from sphere.dynamism.jump_rate import compute_jump_rate
from sphere.dynamism.stability import compute_stability_index

__all__ = [
    "compute_dynamism",
    "build_trajectory",
    "compress_trajectory",
    "compute_transition_matrix",
    "compute_transition_probabilities",
    "compute_curvature",
    "compute_jump_rate",
    "compute_stability_index",
]
