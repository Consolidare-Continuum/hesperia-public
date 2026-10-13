# HESPERIA — RAD. HSPR Calibration Index + grid calibration.

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from hesperia.extensions.dynamics.calibration import (
    calibrate_parameter_grid,
    compute_hspr_calibration_index,
)

_REPO = Path(__file__).resolve().parent.parent


def test_hspr_calibration_index_is_bounded():
    result = compute_hspr_calibration_index(
        stability_score=0.8,
        source_alignment=2.0,
        energy_value=0.3,
        contradiction_load=0.4,
        diffusion_load=0.2,
        resistance_load=0.1,
    )
    hci = result["hspr_calibration_index"]
    assert 0.0 <= hci <= 1.0


def test_calibrate_parameter_grid_basic():
    family_count = 2

    field_init = np.array([0.0, 0.0], dtype=float)
    adjacency_matrix = np.array(
        [
            [0.0, 1.0],
            [1.0, 0.0],
        ],
        dtype=float,
    )
    resistance_vector = np.array([0.1, 0.1], dtype=float)
    contradiction_matrix = np.array(
        [
            [0.0, 0.2],
            [0.2, 0.0],
        ],
        dtype=float,
    )

    documents = [
        {
            "source_vector": [1.0, 0.0],
            "weight": 1.0,
            "quality": 1.0,
            "mass": 1.0,
            "timestamp": 0.0,
        }
    ]

    grid = {
        "alpha": [0.1, 0.2],
        "beta": [0.05],
        "gamma": [0.1],
        "delta": [0.3, 0.4],
        "mu": [0.0],
        "dt": [1.0],
    }

    result = calibrate_parameter_grid(
        field_init=field_init,
        adjacency_matrix=adjacency_matrix,
        resistance_vector=resistance_vector,
        contradiction_matrix=contradiction_matrix,
        documents=documents,
        family_count=family_count,
        grid=grid,
        max_steps=10,
        top_k=2,
    )

    assert result["candidate_count"] == 4
    assert result["best"] is not None
    assert 0.0 <= result["best"]["hspr_calibration_index"] <= 1.0
    assert len(result["top_k"]) == 2


def test_run_field_calibration_cli_three_artifacts():
    cfg = {
        "family_count": 2,
        "families_per_area": 1,
        "area_count": 2,
        "adjacency_matrix": [[0.0, 1.0], [1.0, 0.0]],
        "resistance_vector": [0.1, 0.1],
        "contradiction_matrix": [[0.0, 0.1], [0.1, 0.0]],
        "initial_field": [0.2, 0.2],
        "documents": [{"source_vector": [1.0, 0.0]}],
        "parameter_grid": {
            "alpha": [0.1],
            "beta": [0.05],
            "gamma": [0.0],
            "delta": [0.2],
            "mu": [0.0],
            "dt": [1.0],
        },
        "max_steps": 5,
        "top_k": 1,
    }
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "run_output_e2e_field_calibration.json"
        cfg_path = Path(td) / "c.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.semantic_field.run_field_calibration",
                "--config",
                str(cfg_path),
                "--output",
                str(base),
            ],
            cwd=str(_REPO),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
        assert base.is_file()
        assert (Path(td) / "run_output_e2e_field_calibration_best.json").is_file()
        assert (Path(td) / "run_output_e2e_field_calibration_topk.json").is_file()
        full = json.loads(base.read_text(encoding="utf-8"))
        assert full["schema"] == "hspr_field_calibration_v1"
        assert full["best"] is not None
        assert "area_field_final" in full["best"]
