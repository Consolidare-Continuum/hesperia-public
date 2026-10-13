# HESPERIA — KAM SISR unit tests
from __future__ import annotations

import pytest

from sphere.kam.sisr import compute_sisr, path_overlap


class TestPathOverlap:
    def test_full_overlap(self) -> None:
        paths = ["a", "b", "c"]
        assert path_overlap(paths, paths) == pytest.approx(1.0)

    def test_half_overlap(self) -> None:
        assert path_overlap(["a", "b"], ["a", "c"]) == pytest.approx(0.5)

    def test_empty_baseline_helper_returns_zero(self) -> None:
        assert path_overlap([], ["a"]) == 0.0


class TestComputeSisr:
    def test_empty_pi_star_emits_null(self) -> None:
        r = compute_sisr([0.9, 0.8], baseline_path_count=0)
        assert r.empty_baseline is True
        assert r.SISR_min is None
        assert r.SISR_mean is None

    def test_single_perturbation_min_equals_mean(self) -> None:
        r = compute_sisr([0.625], baseline_path_count=4)
        assert r.SISR_min == pytest.approx(0.625)
        assert r.SISR_mean == pytest.approx(0.625)

    def test_min_and_mean(self) -> None:
        r = compute_sisr([0.75, 0.5], baseline_path_count=4)
        assert r.SISR_min == pytest.approx(0.5)
        assert r.SISR_mean == pytest.approx(0.625)

    def test_no_active_perturbations_null(self) -> None:
        r = compute_sisr([], baseline_path_count=3)
        assert r.SISR_min is None
        assert r.SISR_mean is None
        assert r.empty_baseline is False
