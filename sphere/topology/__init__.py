# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

# Layer-4 topology graph loader and data structures (icosahedral surface graph).
from sphere.topology.topology_loader import (
    load_area_adjacency,
    load_family_area_mapping,
    build_topology_graph,
    load_all,
    validate_icosahedral,
    get_icosahedral_adjacency,
    canonical_edge_list,
    get_canonical_edges,
    topology_fingerprint,
    NUM_AREAS,
    ICOSAHEDRAL_DEGREE,
    ICOSAHEDRAL_EDGES,
    META_AREA_INDICES,
)
from sphere.topology.area_structure import (
    load_area_structure_tfp,
    get_operational_area_neighbors,
    get_area_distance_matrix,
)
from sphere.topology.family_structure import (
    load_families_master,
    load_families_structure_tfp,
    get_family_by_id,
    OBSERVABILITY_LEVELS,
)
from sphere.topology.propagation_weights_loader import (
    load_propagation_weights,
    get_within_area_spread,
    get_bridge_weight,
)
from sphere.topology.family_embedding import (
    load_family_embedding_tfp,
    get_area_zones,
    get_bridges,
    get_composite_family_id,
    ZONE_KEYS,
    ZONE_COUNTS,
)
from sphere.topology.activation_propagation import (
    normalize_scores,
    propagate_within_area,
    propagate_across_bridges,
    recompute_area_scores,
    propagate_activation,
)

__all__ = [
    "load_area_adjacency",
    "load_family_area_mapping",
    "build_topology_graph",
    "load_all",
    "validate_icosahedral",
    "get_icosahedral_adjacency",
    "canonical_edge_list",
    "get_canonical_edges",
    "topology_fingerprint",
    "NUM_AREAS",
    "ICOSAHEDRAL_DEGREE",
    "ICOSAHEDRAL_EDGES",
    "META_AREA_INDICES",
    "load_area_structure_tfp",
    "get_operational_area_neighbors",
    "get_area_distance_matrix",
    "load_families_master",
    "load_families_structure_tfp",
    "get_family_by_id",
    "OBSERVABILITY_LEVELS",
    "load_family_embedding_tfp",
    "get_area_zones",
    "get_bridges",
    "get_composite_family_id",
    "ZONE_KEYS",
    "ZONE_COUNTS",
    "normalize_scores",
    "propagate_within_area",
    "propagate_across_bridges",
    "recompute_area_scores",
    "propagate_activation",
    "load_propagation_weights",
    "get_within_area_spread",
    "get_bridge_weight",
]
