# HESPERIA — RAD. Sealed multiscale stack + HSPR index.

from __future__ import annotations

from pathlib import Path

from core.engine.hex_dynamics import LocalHexMicrophysicsParams, step_hex_local_microphysics
from core.engine.hspr_index import compute_hspr_index
from core.engine.sealed_multiscale_stack import run_sealed_multiscale_stack


def test_step_hex_local_microphysics_nonneg():
    import numpy as np

    nf, nh = 3, 6
    a = np.random.RandomState(0).rand(nf, nh) * 0.2
    r = np.full((nf, nh), 0.2)
    c = np.zeros((nf, nf))
    c[0, 1] = c[1, 0] = 0.1
    a1 = step_hex_local_microphysics(a, r, c, params=LocalHexMicrophysicsParams(alpha=0.05, beta=0.02, gamma=0.01))
    assert (a1 >= 0).all()


def test_compute_hspr_index():
    out = compute_hspr_index(
        {
            "activation_energy": 100.0,
            "propagation_strength": 0.02,
            "contradiction_pressure": 2.0,
            "narrative_density": 0.01,
        }
    )
    assert 0.0 <= out["hspr_index"] <= 1.0
    assert "components_hat" in out


def test_run_sealed_multiscale_stack_smoke():
    root = Path(__file__).resolve().parents[2]
    assets = root / "assets" / "lexicon" / "curated"
    out = run_sealed_multiscale_stack("justice fairness order care trust", assets, use_triz_contradiction=False)
    assert out["execution_flow"] == "sealed_multiscale_v1"
    assert out.get("pch_bundle_version") == "v1"
    assert len(out["family_activation_vector"]) == 288
    assert len(out["area_activation_vector"]) == 12
    assert "hspr_index" in out
    assert out["hspr_index"] >= 0
    assert "contradiction_pressure" in out
    assert "hotspot_map" in out
    assert out.get("hex_energy_mode") == "soft"
    assert len(out.get("hex_energy_trace", [])) == 2
    assert out["hex_energy_trace"][1] <= out["hex_energy_trace"][0] + 1e-3
