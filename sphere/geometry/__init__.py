# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

# Structural geometry: family/area specs, loader, topological boundary validation.

from sphere.geometry.geometry_loader import (
    load_family_geometry,
    load_area_geometry,
    build_geometry_index,
    ALLOWED_BOUNDARY_CLASSES,
    ALLOWED_BOUNDARY_TYPES,
    ALLOWED_GEOMETRY_ROLES,
)
from sphere.geometry.boundary_validator import validate_topological_boundaries

__all__ = [
    "load_family_geometry",
    "load_area_geometry",
    "build_geometry_index",
    "validate_topological_boundaries",
    "ALLOWED_BOUNDARY_CLASSES",
    "ALLOWED_BOUNDARY_TYPES",
    "ALLOWED_GEOMETRY_ROLES",
]
