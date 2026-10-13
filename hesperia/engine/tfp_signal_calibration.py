# HESPERIA — Shared TFP calibration loaders and invariant-path parameters.
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
TFP_DATA_DIR = REPO_ROOT / "assets" / "data" / "engine_dynamics_v060" / "tfp"
TFP_SIGNAL_CALIBRATION_PATH = TFP_DATA_DIR / "tfp_signal_calibration_v2.json"
AREA_INHIBITION_MATRIX_PATH = TFP_DATA_DIR / "area_inhibition_matrix_tfp.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_area_ids(area_ids: list[Any]) -> list[str]:
    if len(area_ids) != 12:
        raise ValueError("TFP area_ids must contain exactly 12 entries")
    out = [str(x) for x in area_ids]
    if len(set(out)) != 12:
        raise ValueError("TFP area_ids must be unique")
    return out


@lru_cache(maxsize=1)
def load_tfp_signal_calibration() -> dict[str, Any]:
    if not TFP_SIGNAL_CALIBRATION_PATH.is_file():
        raise FileNotFoundError(f"missing TFP signal calibration: {TFP_SIGNAL_CALIBRATION_PATH}")
    data = _load_json(TFP_SIGNAL_CALIBRATION_PATH)
    data["area_ids"] = _validate_area_ids(list(data.get("area_ids") or []))
    tm = data.get("temporal_momentum") or {}
    for key in ("alpha1", "alpha2"):
        val = float(tm.get(key) or 0.0)
        if not math.isfinite(val):
            raise ValueError(f"invalid temporal momentum coefficient: {key}")
        tm[key] = val
    data["temporal_momentum"] = tm
    return data


@lru_cache(maxsize=1)
def load_area_inhibition_matrix() -> dict[str, Any]:
    if not AREA_INHIBITION_MATRIX_PATH.is_file():
        raise FileNotFoundError(f"missing TFP area inhibition matrix: {AREA_INHIBITION_MATRIX_PATH}")
    data = _load_json(AREA_INHIBITION_MATRIX_PATH)
    area_ids = _validate_area_ids(list(data.get("area_ids") or []))
    matrix = data.get("matrix")
    if not isinstance(matrix, list) or len(matrix) != 12:
        raise ValueError("TFP inhibition matrix must be a 12x12 list")
    rows: list[list[float]] = []
    for i, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != 12:
            raise ValueError("TFP inhibition matrix must be a 12x12 list")
        vals: list[float] = []
        for j, item in enumerate(row):
            val = float(item)
            if not math.isfinite(val):
                raise ValueError("TFP inhibition matrix contains NaN or inf")
            if i == j and abs(val) > 1e-12:
                raise ValueError("TFP inhibition matrix diagonal must be zero")
            vals.append(val)
        rows.append(vals)
    data["area_ids"] = area_ids
    data["matrix"] = rows
    return data


def load_tfp_runtime_bundle() -> dict[str, Any]:
    calibration = load_tfp_signal_calibration()
    inhibition = load_area_inhibition_matrix()
    if inhibition.get("area_ids") != calibration.get("area_ids"):
        raise ValueError("TFP calibration and inhibition matrix area_ids do not match")
    return {"calibration": calibration, "inhibition_matrix": inhibition}


def get_area_ids() -> list[str]:
    return list(load_tfp_signal_calibration()["area_ids"])


def get_area_curve_map() -> dict[str, str]:
    return dict(load_tfp_signal_calibration().get("area_curve_map") or {})


def get_curve_calibration_reference() -> dict[str, float]:
    return dict(load_tfp_signal_calibration().get("curve_calibration_reference") or {})


def get_default_session_topology_run_params() -> dict[str, Any]:
    cfg = load_tfp_signal_calibration()
    base = dict(cfg.get("session_topology_defaults") or {})
    base.setdefault("window_size", 80)
    base.setdefault("normalize_scores", True)
    base.setdefault("include_curve_projection_meta", True)
    base["curve_smooth_alpha"] = cfg.get("curve_smooth_alpha")
    base["curve_session_center"] = bool(cfg.get("curve_session_center"))
    base["apply_token_negation"] = bool(cfg.get("apply_token_negation"))
    base["negation_window"] = int(cfg.get("negation_window") or 2)
    base["negation_multiplier"] = float(cfg.get("negation_multiplier") or 0.5)
    base["per_concept_score_cap"] = float(cfg.get("concept_cap") or 8.0)
    base["use_log1p_concept_scores"] = bool(cfg.get("log_normalization_enabled"))
    base["evidence_volume_normalize"] = True
    return base


AREA_IDS = get_area_ids()
AREA_CURVE_MAP = get_area_curve_map()
CURVE_CALIBRATION_REFERENCE = get_curve_calibration_reference()
DEFAULT_SESSION_TOPOLOGY_RUN_PARAMS = get_default_session_topology_run_params()
