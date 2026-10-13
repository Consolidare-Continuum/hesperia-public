# HESPERIA — GTP (General Thought Propagation) package.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Implements GTP-01..GTP-06 from
docs/brain-export/operational/assignments/HESPERIA-FORMALIZATION-GENERAL-THOUGHT-PROPAGATION-v0_1.md
(23_SPEC__General_Thought_Propagation_and_Hex_Orientation_v0_1), depending on the
PointZero-scoped slice of 22_SPEC__ (Geodesic Sphere + IPoW) it needs.
"""

from __future__ import annotations

from sphere.topology.gtp.coherence import (
    NUM_AREAS,
    NUM_FAMILIES,
    VECTOR_DIM,
    CoherenceField,
    broadcast,
    coherence_scalar,
    compute_coherence_field,
    get_area_anchor_directions,
    get_family_anchor_directions,
)
from sphere.topology.gtp.gtpa import GTPAResult, coherence_align, gtpa_next_hex, path_prior, score
from sphere.topology.gtp.imprint import (
    ImprintDifference,
    ThoughtImprint,
    build_thought_imprint,
    imprint_difference,
)
from sphere.topology.gtp.ipow import POINT_ZERO, InteriorPointOfWorldView, point_zero, point_zero_delta, step_delta
from sphere.topology.gtp.neighbors import HexCell, legal_neighbors
from sphere.topology.gtp.pipeline import GtpStepResult, gtp_step_to_dict, run_gtp_step
from sphere.topology.gtp.rotation import (
    input_features,
    match_logical,
    match_semantic,
    select_hex_rotation,
    side_active,
    side_match_score,
    side_specs_for_rotation,
)
from sphere.topology.gtp.side_operators import (
    FARA,
    SIDE_SPECS,
    LogicalOperator,
    SemanticOperator,
    SideSpec,
    logical_test,
    side_spec,
    validate_registry,
)

__all__ = [
    "NUM_AREAS",
    "NUM_FAMILIES",
    "VECTOR_DIM",
    "CoherenceField",
    "broadcast",
    "coherence_scalar",
    "compute_coherence_field",
    "get_area_anchor_directions",
    "get_family_anchor_directions",
    "GTPAResult",
    "coherence_align",
    "gtpa_next_hex",
    "path_prior",
    "score",
    "ImprintDifference",
    "ThoughtImprint",
    "build_thought_imprint",
    "imprint_difference",
    "POINT_ZERO",
    "InteriorPointOfWorldView",
    "point_zero",
    "point_zero_delta",
    "step_delta",
    "HexCell",
    "legal_neighbors",
    "GtpStepResult",
    "gtp_step_to_dict",
    "run_gtp_step",
    "input_features",
    "match_logical",
    "match_semantic",
    "select_hex_rotation",
    "side_active",
    "side_match_score",
    "side_specs_for_rotation",
    "FARA",
    "SIDE_SPECS",
    "LogicalOperator",
    "SemanticOperator",
    "SideSpec",
    "logical_test",
    "side_spec",
    "validate_registry",
]
