# HESPERIA — KAM_semantic_score + kam_verdict unit tests
from __future__ import annotations

import pytest

from sphere.kam.kam_score import compute_kam_semantic_score, verdict_from_score
from sphere.kam.sisr import SisrResult


def _sisr(min_v: float = 0.8, mean_v: float = 0.9) -> SisrResult:
    return SisrResult(
        SISR_min=min_v,
        SISR_mean=mean_v,
        path_survival=(min_v, mean_v),
        empty_baseline=False,
    )


class TestVerdictBands:
    def test_structurally_robust_at_075(self) -> None:
        assert verdict_from_score(0.75) == "structurally_robust"

    def test_conditionally_stable_lower_inclusive(self) -> None:
        assert verdict_from_score(0.45) == "conditionally_stable"

    def test_conditionally_stable_mid(self) -> None:
        assert verdict_from_score(0.58) == "conditionally_stable"

    def test_fragile_below_045(self) -> None:
        assert verdict_from_score(0.449999) == "fragile_trajectory"

    def test_null_insufficient(self) -> None:
        assert verdict_from_score(None) == "insufficient_baseline"

    def test_just_below_robust(self) -> None:
        assert verdict_from_score(0.749999) == "conditionally_stable"


class TestCompositeScore:
    def test_multiplicative_collapse_on_zero_factor(self) -> None:
        r = compute_kam_semantic_score(
            _sisr(0.9, 0.95),
            area_drift_mean=0.0,
            contradiction_growth_mean=0.0,
            family_resonance_mean=0.0,  # collapses
            dominant_area_flip_rate=0.0,
        )
        assert r.KAM_semantic_score == pytest.approx(0.0)
        assert r.kam_verdict == "fragile_trajectory"

    def test_empty_baseline_insufficient(self) -> None:
        empty = SisrResult(
            SISR_min=None,
            SISR_mean=None,
            path_survival=(),
            empty_baseline=True,
        )
        r = compute_kam_semantic_score(
            empty,
            area_drift_mean=0.0,
            contradiction_growth_mean=0.0,
            family_resonance_mean=1.0,
            dominant_area_flip_rate=0.0,
        )
        assert r.KAM_semantic_score is None
        assert r.kam_verdict == "insufficient_baseline"

    def test_default_uses_sisr_min_for_path_survival(self) -> None:
        r = compute_kam_semantic_score(
            _sisr(0.5, 1.0),
            area_drift_mean=0.0,
            contradiction_growth_mean=0.0,
            family_resonance_mean=1.0,
            dominant_area_flip_rate=0.0,
        )
        assert r.components is not None
        assert r.components.path_survival == pytest.approx(0.5)
        assert r.KAM_semantic_score == pytest.approx(0.5)
