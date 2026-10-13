# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

# HESPERIA Interface Layer — external system access to pipeline and USF.

from sphere.interfaces.structural_api import (
    analyze_text,
    ERROR_CONFIG_ERROR,
    ERROR_GUARD_VIOLATION,
    ERROR_INPUT_VALIDATION,
    ERROR_PIPELINE_ERROR,
    ERROR_UNKNOWN_ERROR,
)
from sphere.interfaces.usf_api import (
    get_usf,
    serialize_usf,
    save_usf,
    compare_usf,
)
from sphere.interfaces.debug_interface import debug_pipeline
from sphere.interfaces.interface_validation import (
    validate_text_input,
    validate_config,
    validate_layer_request,
    DEFAULT_MAX_TEXT_LENGTH,
)

__all__ = [
    "analyze_text",
    "get_usf",
    "serialize_usf",
    "save_usf",
    "compare_usf",
    "debug_pipeline",
    "validate_text_input",
    "validate_config",
    "validate_layer_request",
    "DEFAULT_MAX_TEXT_LENGTH",
    "ERROR_INPUT_VALIDATION",
    "ERROR_CONFIG_ERROR",
    "ERROR_PIPELINE_ERROR",
    "ERROR_GUARD_VIOLATION",
    "ERROR_UNKNOWN_ERROR",
]
