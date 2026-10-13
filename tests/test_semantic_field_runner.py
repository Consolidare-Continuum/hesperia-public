# HESPERIA — RAD. runtime.semantic_field runner smoke tests.
# Load runner by file path (avoid importing as tests.* package).

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent


def _load_run_semantic_field():
    path = _REPO / "runtime" / "semantic_field" / "run_semantic_field.py"
    spec = importlib.util.spec_from_file_location("hesperia_run_semantic_field", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.run_semantic_field


run_semantic_field = _load_run_semantic_field()


def test_run_semantic_field_small_explicit_matrices():
    w = np.array([[0.0, 1.0], [1.0, 0.0]])
    c = np.zeros((2, 2))
    cfg = {
        "family_count": 2,
        "families_per_area": 1,
        "area_count": 2,
        "adjacency_matrix": w.tolist(),
        "resistance_vector": [0.1, 0.1],
        "contradiction_matrix": c.tolist(),
        "initial_field": [0.5, 0.5],
        "alpha": 0.1,
        "beta": 0.05,
        "gamma": 0.0,
        "delta": 0.2,
        "dt": 1.0,
        "epsilon": 1e-3,
        "tau": 1e-3,
        "documents": [{"source_vector": [1.0, 0.0], "quality": 1.0}],
        "max_steps": 5,
    }
    out = run_semantic_field(cfg)
    assert len(out["family_field_final"]) == 2
    assert len(out["area_field_final"]) == 2
    assert out["steps"] <= 5
    assert len(out["timeline"]) == out["steps"]
    assert len(out["energy_prev_trajectory"]) == out["steps"]


def test_run_semantic_field_ring_shortcuts():
    cfg = {
        "family_count": 4,
        "families_per_area": 2,
        "area_count": 2,
        "adjacency_mode": "canonical_ring",
        "contradiction_zero": True,
        "resistance_vector": 0.2,
        "initial_mode": "uniform",
        "alpha": 0.05,
        "beta": 0.05,
        "gamma": 0.0,
        "delta": 0.3,
        "documents": [{"source_family_index": 0, "weight": 1.0}],
        "max_steps": 3,
    }
    out = run_semantic_field(cfg)
    assert len(out["family_field_final"]) == 4
    assert out["steps"] >= 1


def test_cli_writes_json():
    cfg = {
        "family_count": 2,
        "families_per_area": 1,
        "area_count": 2,
        "adjacency_matrix": [[0, 1], [1, 0]],
        "resistance_vector": [0.1, 0.1],
        "contradiction_matrix": [[0, 0], [0, 0]],
        "initial_field": [0.4, 0.6],
        "alpha": 0.1,
        "beta": 0.1,
        "gamma": 0.0,
        "delta": 0.1,
        "documents": [{"source_vector": [0.5, 0.5]}],
        "max_steps": 2,
    }
    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "c.json"
        out_path = Path(td) / "o.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "runtime.semantic_field.run_semantic_field",
                "--config",
                str(cfg_path),
                "--output",
                str(out_path),
            ],
            cwd=str(_REPO),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert "family_field_final" in data
