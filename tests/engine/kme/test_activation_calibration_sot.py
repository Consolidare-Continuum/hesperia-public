# HESPERIA — Tests: activation floor SoT (CHI-B16-02)
"""clinical_bridge thresholds must come from activation_calibration, not a second hardcoded copy."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def test_activation_calibration_yaml_path_exists() -> None:
    from hesperia.engine.calibration.activation_calibration import _default_calibration_yaml

    path = _default_calibration_yaml()
    assert path.exists(), f"missing canon YAML: {path}"
    assert path.name == "activation_calibration.yaml"


def test_clinical_bridge_thresholds_match_calibration_getters() -> None:
    from hesperia.engine.calibration.activation_calibration import (
        get_activation_threshold,
        get_area_active_threshold,
        load_calibration_config,
    )
    import hesperia.engine.kme.clinical_bridge as cb

    loaded = load_calibration_config()
    assert loaded.get("activation_threshold") == 0.01
    assert loaded.get("area_active_threshold") == 0.05
    assert cb.ACTIVATION_THRESHOLD == get_activation_threshold() == 0.01
    assert cb.AREA_ACTIVE_THRESHOLD == get_area_active_threshold() == 0.05


def test_clinical_bridge_imports_calibration_module() -> None:
    import hesperia.engine.kme.clinical_bridge as cb

    assert hasattr(cb, "get_activation_threshold")
    assert hasattr(cb, "load_calibration_config")
    assert cb.get_activation_threshold is not None
