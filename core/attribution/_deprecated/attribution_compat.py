# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
DEPRECATED — Do not use in new code. Use core.attribution.structural instead.
Re-exports for backward compatibility only; RAD: no version in filename.
"""
from __future__ import annotations

from core.attribution.structural import (
    DEFAULT_TEXT_CAP,
    aggregate_dominant,
    attribute,
    build_region_seed,
    load_dict_a,
    load_dict_b,
    normalize,
    run_attribution_pipeline,
    tokenize,
)

# Old names (strip version in new code)
load_dict_a_v033 = load_dict_a
load_dict_b_v033 = load_dict_b

__all__ = [
    "DEFAULT_TEXT_CAP",
    "aggregate_dominant",
    "attribute",
    "build_region_seed",
    "load_dict_a",
    "load_dict_b",
    "load_dict_a_v033",
    "load_dict_b_v033",
    "normalize",
    "run_attribution_pipeline",
    "tokenize",
]
