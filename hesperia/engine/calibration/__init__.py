# HESPERIA — Engine calibration (activation thresholds + HSPR field index)
from hesperia.engine.calibration.activation_calibration import (
    calibrate_thresholds_from_corpus,
    get_activation_threshold,
    get_area_active_threshold,
)
from hesperia.engine.calibration.hspr_field import (
    HSPRWeights,
    ObservableScales,
    compute_hspr,
    hspr_from_observables,
    hspr_payload,
    interpret_hspr,
    normalize_observables,
)

__all__ = [
    "get_activation_threshold",
    "get_area_active_threshold",
    "calibrate_thresholds_from_corpus",
    "HSPRWeights",
    "ObservableScales",
    "normalize_observables",
    "compute_hspr",
    "hspr_from_observables",
    "interpret_hspr",
    "hspr_payload",
]
