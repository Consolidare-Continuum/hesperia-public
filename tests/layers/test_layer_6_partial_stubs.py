# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from the author.
# See LEGAL_NOTICE.md for full terms.

"""HES-MATH-BEHAV-54..58 — L6 gradient/curvature/Group-IV PARTIAL inventory + sealed defaults."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.layers.layer_6 import (
    L6_PARTIAL_CURVATURE_SLOTS,
    L6_PARTIAL_GRADIENT_SLOTS,
    L6_PARTIAL_GROUP_IV_SLOTS,
    compute_L6,
)


def test_l6_partial_slot_inventory_complete() -> None:
    """HES-MATH-BEHAV-54: reserved gradient / curvature / Group-IV names are enumerated."""
    assert set(L6_PARTIAL_GRADIENT_SLOTS) == {"COVERAGE_GRADIENT", "ENTROPY_GRADIENT"}
    assert set(L6_PARTIAL_CURVATURE_SLOTS) == {
        "SECOND_ORDER_RESPONSE",
        "DOMINANCE_CURVATURE",
        "ENTROPY_CURVATURE",
    }
    assert set(L6_PARTIAL_GROUP_IV_SLOTS) == {
        "POTENTIAL_GRADIENT",
        "ESCAPE_ENERGY_THRESHOLD",
        "FORCE_ANALOG_MAGNITUDE",
        "MONOTONICITY_CHECK",
        "FIXED_POINT_DETECTION",
        "CYCLE_DETECTION_FUNCTIONAL",
    }


def test_l6_partial_stubs_keep_sealed_identity() -> None:
    """Without perturbation, PARTIAL slots stay safe identity constants (no invented FD)."""
    l1 = {"NORMALIZED_FAMILY_ENTROPY": 0.25}
    l2 = {"MASS_AT_DEPTH": [4.0, 2.0, 1.0]}
    out = compute_L6(l1, l2)
    assert out["COVERAGE_GRADIENT"] == 0.0
    assert out["ENTROPY_GRADIENT"] == 0.0
    assert out["SECOND_ORDER_RESPONSE"] == 0.0
    assert out["DOMINANCE_CURVATURE"] == 0.0
    assert out["ENTROPY_CURVATURE"] == 0.0
    assert out["POTENTIAL_GRADIENT"] == 0.0
    assert out["ESCAPE_ENERGY_THRESHOLD"] == 1.0
    assert out["FORCE_ANALOG_MAGNITUDE"] == 0.0
    assert out["MONOTONICITY_CHECK"] is True
    assert out["FIXED_POINT_DETECTION"] is True
    assert out["CYCLE_DETECTION_FUNCTIONAL"] is False
    # Live depth fields still compute from MASS_AT_DEPTH (ratio uses +eps).
    assert abs(out["DEPTH_GROWTH_RATIO"] - 0.5) < 1e-9
    assert out["FIBONACCI_DEVIATION_SCORE"] == abs(1.0 - (2.0 + 4.0))
    # Composite from sealed CONDITION_NUMBER=1, LYAPUNOV=0 → 0.5
    assert abs(out["GLOBAL_STABILITY_SCORE"] - 0.5) < 1e-12


def test_l6_ignores_perturbation_series_until_explicitly_enabled() -> None:
    """Supplying E(x±ε) data alone must not change the sealed default path."""
    l1 = {
        "COVERAGE_RATIO": 0.4,
        "FAMILY_ENTROPY": 0.5,
        "DOMINANCE_RATIO": 0.6,
        "DOMINANT_FAMILY_ID": 4,
        "NORMALIZED_FAMILY_ENTROPY": 0.25,
    }
    series = {
        "epsilon_magnitude": 0.5,
        "base_output": [1.0, 3.0],
        "plus": {
            "l1": {
                "COVERAGE_RATIO": 0.5,
                "FAMILY_ENTROPY": 0.7,
                "DOMINANCE_RATIO": 0.8,
                "DOMINANT_FAMILY_ID": 5,
            },
            "output": [3.0, 5.0],
        },
    }

    out = compute_L6(l1, {}, perturbation_series=series)

    assert out["COVERAGE_GRADIENT"] == 0.0
    assert out["DOMINANCE_CURVATURE"] == 0.0
    assert out["POTENTIAL_GRADIENT"] == 0.0


def test_l6_computes_39_spec_finite_differences_from_complete_series() -> None:
    """HES-MATH-BEHAV-55/56/57: use supplied E(x±ε), never inferred physics."""
    l1 = {
        "COVERAGE_RATIO": 0.4,
        "FAMILY_ENTROPY": 0.5,
        "DOMINANCE_RATIO": 0.6,
        "DOMINANT_FAMILY_ID": 4,
        "NORMALIZED_FAMILY_ENTROPY": 0.25,
    }
    series = {
        "epsilon_magnitude": 0.5,
        "base_output": [1.0, 3.0],
        "base_input_intensity": 1.0,
        "plus": {
            "l1": {
                "COVERAGE_RATIO": 0.5,
                "FAMILY_ENTROPY": 0.7,
                "DOMINANCE_RATIO": 0.8,
                "DOMINANT_FAMILY_ID": 5,
            },
            "output": [3.0, 5.0],
            "input_intensity": 1.5,
        },
        "minus": {
            "l1": {
                "COVERAGE_RATIO": 0.3,
                "FAMILY_ENTROPY": 0.4,
                "DOMINANCE_RATIO": 0.5,
                "DOMINANT_FAMILY_ID": 4,
            },
            "output": [0.0, 2.0],
            "input_intensity": 0.5,
        },
        "input_vector": [0.25, 0.75],
        "iterate_2_output": [1.0, 3.0],
        "iterate_3_output": [0.25, 0.75],
    }

    out = compute_L6(
        l1,
        {},
        perturbation_enabled=True,
        perturbation_series=series,
    )

    first_denominator = 0.5 + 1e-12
    second_denominator = 0.25 + 1e-12
    assert out["INPUT_PERTURBATION_RESPONSE"] == pytest.approx(
        math.sqrt(8.0) / first_denominator
    )
    assert out["DOMINANT_FAMILY_STABILITY"] is False
    assert out["COVERAGE_GRADIENT"] == pytest.approx(0.1 / first_denominator)
    assert out["ENTROPY_GRADIENT"] == pytest.approx(0.2 / first_denominator)
    assert out["SECOND_ORDER_RESPONSE"] == pytest.approx(
        math.sqrt(2.0) / second_denominator
    )
    assert out["DOMINANCE_CURVATURE"] == pytest.approx(0.1 / second_denominator)
    assert out["ENTROPY_CURVATURE"] == pytest.approx(0.1 / second_denominator)
    assert out["POTENTIAL_GRADIENT"] == pytest.approx(0.2)
    assert out["ESCAPE_ENERGY_THRESHOLD"] == pytest.approx(0.5)
    assert out["FORCE_ANALOG_MAGNITUDE"] == pytest.approx(0.2 / first_denominator)
    assert out["MONOTONICITY_CHECK"] is True
    assert out["FIXED_POINT_DETECTION"] is True
    assert out["CYCLE_DETECTION_FUNCTIONAL"] is True


def test_l6_enabled_path_leaves_missing_measurements_at_sealed_defaults() -> None:
    """An incomplete hook computes only supported formulas and preserves other identities."""
    l1 = {
        "COVERAGE_RATIO": 0.4,
        "FAMILY_ENTROPY": 0.5,
        "DOMINANCE_RATIO": 0.6,
        "DOMINANT_FAMILY_ID": 4,
        "NORMALIZED_FAMILY_ENTROPY": 0.25,
    }
    series = {
        "epsilon_magnitude": 0.25,
        "plus": {
            "l1": {
                "COVERAGE_RATIO": 0.45,
                "FAMILY_ENTROPY": 0.55,
                "DOMINANCE_RATIO": 0.7,
                "DOMINANT_FAMILY_ID": 4,
            },
        },
    }

    out = compute_L6(
        l1,
        {},
        perturbation_enabled=True,
        perturbation_series=series,
    )

    assert out["COVERAGE_GRADIENT"] > 0.0
    assert out["SECOND_ORDER_RESPONSE"] == 0.0
    assert out["DOMINANCE_CURVATURE"] == 0.0
    assert out["FIXED_POINT_DETECTION"] is True
    assert out["CYCLE_DETECTION_FUNCTIONAL"] is False
