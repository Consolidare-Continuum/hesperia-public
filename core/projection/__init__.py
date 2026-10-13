# HESPERIA — Public projection package.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Public projection package.

- **Classifier:** ``area_math_grain`` — ``HESPERIA_AREA_MATH_GRAIN=12|10``
- **Default grain = 12** — ``default_twelve``
- **Optional grain = 10** — ``ten_area_module`` + ``public_projection_layer``
"""

from core.projection.area_math_grain import (
    active_area_count,
    active_family_count,
    area_math_classifier_meta,
    area_math_grain,
    area_math_totals,
    classify_area_math_grain,
    pack_excludes_area,
    pack_excludes_family,
    project_macro_for_grain,
    slice_area_vector,
    slice_family_vector,
    ten_area_module_enabled,
)
from core.projection.default_twelve import area_name_at, project_default_twelve_macro
from core.projection.public_projection_layer import (
    apply_public_projection,
    filter_reserved_structures,
    project_public_areas,
    project_public_families,
    project_public_metrics,
    sanitize_public_trace,
)
from core.projection.ten_area_module import (
    TEN_AREA_COUNT,
    TEN_AREA_FAMILY_COUNT,
    project_ten_area_macro,
)

__all__ = [
    "TEN_AREA_COUNT",
    "TEN_AREA_FAMILY_COUNT",
    "active_area_count",
    "active_family_count",
    "apply_public_projection",
    "area_math_classifier_meta",
    "area_math_grain",
    "area_math_totals",
    "area_name_at",
    "classify_area_math_grain",
    "filter_reserved_structures",
    "pack_excludes_area",
    "pack_excludes_family",
    "project_default_twelve_macro",
    "project_macro_for_grain",
    "project_public_areas",
    "project_public_families",
    "project_public_metrics",
    "project_ten_area_macro",
    "sanitize_public_trace",
    "slice_area_vector",
    "slice_family_vector",
    "ten_area_module_enabled",
]
