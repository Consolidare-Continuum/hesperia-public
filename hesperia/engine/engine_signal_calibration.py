# HESPERIA — Engine dynamics calibration (invariant path, mainline).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
#
# Canonical loaders for sealed product: signal JSON + area inhibition matrix.
# Legacy paths under assets/.../tfp/ remain as fallback only (research / old bundles).

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_DYNAMICS_V060 = REPO_ROOT / "assets" / "data" / "engine_dynamics_v060"
_SEMANTIC = ENGINE_DYNAMICS_V060 / "semantic_dynamics"
_TFP_LEGACY = ENGINE_DYNAMICS_V060 / "tfp"


def _signal_calibration_path() -> Path:
    """Prefer mainline semantic_dynamics pin; fallback to legacy tfp bundle."""
    p = _SEMANTIC / "signal_calibration_v2.json"
    if p.is_file():
        return p
    legacy = _TFP_LEGACY / "tfp_signal_calibration_v2.json"
    return legacy


def _inhibition_matrix_path(cal: dict[str, Any]) -> Path:
    """Resolve inhibition file next to signal calibration, then legacy tfp."""
    cal_path = _signal_calibration_path()
    rel = str(cal.get("inhibition_matrix_file") or "area_inhibition_matrix_main_v1.json")
    p = cal_path.parent / rel
    if p.is_file():
        return p
    legacy = _TFP_LEGACY / "area_inhibition_matrix_tfp.json"
    if legacy.is_file():
        return legacy
    # Last resort: main v1 name under semantic_dynamics
    fallback = _SEMANTIC / "area_inhibition_matrix_main_v1.json"
    return fallback


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_area_ids(area_ids: list[Any]) -> list[str]:
    if len(area_ids) != 12:
        raise ValueError("engine area_ids must contain exactly 12 entries")
    out = [str(x) for x in area_ids]
    if len(set(out)) != 12:
        raise ValueError("engine area_ids must be unique")
    return out


@lru_cache(maxsize=1)
def load_engine_signal_calibration() -> dict[str, Any]:
    path = _signal_calibration_path()
    if not path.is_file():
        raise FileNotFoundError(f"missing engine signal calibration: {path}")
    data = _load_json(path)
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
    cal = load_engine_signal_calibration()
    path = _inhibition_matrix_path(cal)
    if not path.is_file():
        raise FileNotFoundError(f"missing area inhibition matrix: {path}")
    data = _load_json(path)
    area_ids = _validate_area_ids(list(data.get("area_ids") or []))
    matrix = data.get("matrix")
    if not isinstance(matrix, list) or len(matrix) != 12:
        raise ValueError("area inhibition matrix must be a 12x12 list")
    rows: list[list[float]] = []
    for i, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != 12:
            raise ValueError("area inhibition matrix must be a 12x12 list")
        vals: list[float] = []
        for j, item in enumerate(row):
            val = float(item)
            if not math.isfinite(val):
                raise ValueError("area inhibition matrix contains NaN or inf")
            if i == j and abs(val) > 1e-12:
                raise ValueError("area inhibition matrix diagonal must be zero")
            vals.append(val)
        rows.append(vals)
    data["area_ids"] = area_ids
    data["matrix"] = rows
    return data


def load_engine_runtime_bundle() -> dict[str, Any]:
    calibration = load_engine_signal_calibration()
    inhibition = load_area_inhibition_matrix()
    if inhibition.get("area_ids") != calibration.get("area_ids"):
        raise ValueError("engine calibration and inhibition matrix area_ids do not match")
    return {"calibration": calibration, "inhibition_matrix": inhibition}


def get_area_ids() -> list[str]:
    return list(load_engine_signal_calibration()["area_ids"])


def get_area_curve_map() -> dict[str, str]:
    return dict(load_engine_signal_calibration().get("area_curve_map") or {})


def get_curve_calibration_reference() -> dict[str, float]:
    return dict(load_engine_signal_calibration().get("curve_calibration_reference") or {})


def get_default_session_topology_run_params() -> dict[str, Any]:
    cfg = load_engine_signal_calibration()
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


# Backward-compatible names (deprecated — prefer load_engine_*).
load_tfp_signal_calibration = load_engine_signal_calibration
load_tfp_runtime_bundle = load_engine_runtime_bundle


AREA_IDS = get_area_ids()
AREA_CURVE_MAP = get_area_curve_map()
CURVE_CALIBRATION_REFERENCE = get_curve_calibration_reference()
DEFAULT_SESSION_TOPOLOGY_RUN_PARAMS = get_default_session_topology_run_params()
