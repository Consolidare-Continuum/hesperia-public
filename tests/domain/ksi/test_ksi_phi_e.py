from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.domain.ksi import PhiEParams, phi_e, phi_e_raw, phi_e_trace, r_e_for_type, sat

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ksi_phi_e_gold_v01.json"


def _p(**kwargs: float) -> PhiEParams:
    defaults = dict(
        a_i=0.5,
        w_e=0.5,
        r_e=1.0,
        q_e=0.6,
        s_e=1.0,
        c_e=0.8,
        p_e=1.0,
        d_e=0.9,
        k_e=0.05,
    )
    defaults.update(kwargs)
    return PhiEParams(**defaults)


class TestSat:
    def test_sat_clamps_high(self) -> None:
        assert sat(1.5) == 1.0

    def test_sat_clamps_low(self) -> None:
        assert sat(-0.3) == 0.0

    def test_sat_identity_in_range(self) -> None:
        assert sat(0.42) == pytest.approx(0.42)


class TestPhiEBoundary:
    def test_zero_source_activation(self) -> None:
        params = _p(a_i=0.0, w_e=1.0, r_e=1.0, q_e=1.0, s_e=1.0, c_e=1.0, p_e=1.0, d_e=1.0, k_e=0.1)
        assert phi_e_raw(params) == pytest.approx(-0.1)
        assert phi_e(params) == 0.0

    def test_all_params_max(self) -> None:
        params = _p(a_i=1.0, w_e=1.0, r_e=1.0, q_e=1.0, s_e=1.0, c_e=1.0, p_e=1.0, d_e=1.0, k_e=0.0)
        assert phi_e(params) == 1.0
        assert phi_e_raw(params) == 1.0

    def test_all_positive_terms_min_nonzero_k(self) -> None:
        params = _p(a_i=0.01, w_e=0.01, r_e=0.5, q_e=0.2, s_e=0.2, c_e=0.2, p_e=1.0, d_e=0.5, k_e=0.5)
        assert phi_e(params) == 0.0

    def test_negative_r_e_saturates_to_zero(self) -> None:
        params = _p(a_i=1.0, w_e=1.0, r_e=-0.7, q_e=1.0, s_e=1.0, c_e=1.0, p_e=1.0, d_e=1.0, k_e=0.0)
        assert phi_e_raw(params) == pytest.approx(-0.7)
        assert phi_e(params) == 0.0

    def test_inhibition_dominates_product(self) -> None:
        params = _p(a_i=1.0, w_e=1.0, r_e=1.0, q_e=1.0, s_e=1.0, c_e=1.0, p_e=1.0, d_e=1.0, k_e=1.5)
        assert phi_e(params) == 0.0


class TestPhiEGoldPairs:
    @pytest.fixture(scope="class")
    def gold_rows(self) -> list[dict]:
        with GOLD_FIXTURES.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload["cases"]

    @pytest.mark.parametrize("case_id", [f"G{i:02d}" for i in range(1, 11)])
    def test_gold_phi_sat(self, gold_rows: list[dict], case_id: str) -> None:
        row = next(r for r in gold_rows if r["id"] == case_id)
        params = PhiEParams(**row["params"])
        assert phi_e(params) == pytest.approx(row["phi_sat"], abs=1e-9)
        assert phi_e_trace(params)["phi_sat"] == pytest.approx(row["phi_sat"], abs=1e-9)


class TestRelationCoefficients:
    def test_loads_activates_coefficient(self) -> None:
        assert r_e_for_type("activates") == 1.0

    def test_unlisted_type_uses_default(self) -> None:
        assert r_e_for_type("unknown_relation_xyz") == 0.5


class TestKsiConfigAsset:
    def test_config_json_present(self) -> None:
        path = REPO_ROOT / "assets" / "data" / "ksi" / "ksi_config_v01.json"
        assert path.is_file()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["thresholds"]["tau"] == 0.25
