# HESPERIA — Activation Threshold Calibration
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
# B1 agentic addresses: docs/recipes/chiron_tweaks/CHIRON-126-ADDRESS-MAP-2026-08-21.md (items 61–62)
"""
Адаптивные пороги активации. Реальные данные требуют калибровки;
по умолчанию используются значения, совместимые с clinical_bridge.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Значения по умолчанию (совместимы с hesperia.engine.kme.clinical_bridge)
DEFAULT_ACTIVATION_THRESHOLD = 0.01
DEFAULT_AREA_ACTIVE_THRESHOLD = 0.05

_CALIBRATION: dict[str, float] = {}


def _default_calibration_yaml() -> Path:
    """Canon path: assets/specs/canon/activation_calibration.yaml (repo root)."""
    return (
        Path(__file__).resolve().parents[3]
        / "assets"
        / "specs"
        / "canon"
        / "activation_calibration.yaml"
    )


def load_calibration_config(path: Path | str | None = None) -> dict[str, float]:
    """Загрузить конфиг калибровки (activation_threshold, area_active_threshold) из YAML."""
    global _CALIBRATION
    if path is None:
        spec = _default_calibration_yaml()
    else:
        spec = Path(path)
    if not spec.exists():
        return {}
    import yaml
    with open(spec, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out = {
        "activation_threshold": float(data.get("activation_threshold", DEFAULT_ACTIVATION_THRESHOLD)),
        "area_active_threshold": float(data.get("area_active_threshold", DEFAULT_AREA_ACTIVE_THRESHOLD)),
    }
    _CALIBRATION.update(out)
    return out


def get_activation_threshold(calibration: dict[str, float] | None = None) -> float:
    """Порог для создания узлов/рёбер по активации (concept/family)."""
    if calibration is not None:
        return float(calibration.get("activation_threshold", DEFAULT_ACTIVATION_THRESHOLD))
    if _CALIBRATION:
        return _CALIBRATION.get("activation_threshold", DEFAULT_ACTIVATION_THRESHOLD)
    return DEFAULT_ACTIVATION_THRESHOLD


def get_area_active_threshold(calibration: dict[str, float] | None = None) -> float:
    """Минимальная оценка области для учёта в area-adjacency edges."""
    if calibration is not None:
        return float(calibration.get("area_active_threshold", DEFAULT_AREA_ACTIVE_THRESHOLD))
    if _CALIBRATION:
        return _CALIBRATION.get("area_active_threshold", DEFAULT_AREA_ACTIVE_THRESHOLD)
    return DEFAULT_AREA_ACTIVE_THRESHOLD


def calibrate_thresholds_from_corpus(
    activation_results: list[dict[str, Any]],
    percentile_concept: float = 5.0,
    percentile_area: float = 10.0,
) -> dict[str, float]:
    """
    По списку результатов активации (с полями concepts, areas) подобрать пороги:
    activation_threshold = percentile_concept от распределения ненулевых concept scores;
    area_active_threshold = percentile_area от distribution area scores.
    """
    all_c: list[float] = []
    all_a: list[float] = []
    for r in activation_results:
        for v in (r.get("concepts") or {}).values():
            if float(v) > 0:
                all_c.append(float(v))
        for v in (r.get("areas") or {}).values():
            if float(v) > 0:
                all_a.append(float(v))
    all_c.sort()
    all_a.sort()
    n_c, n_a = len(all_c), len(all_a)
    idx_c = max(0, int(n_c * percentile_concept / 100) - 1)
    idx_a = max(0, int(n_a * percentile_area / 100) - 1)
    act_thresh = all_c[idx_c] if all_c else DEFAULT_ACTIVATION_THRESHOLD
    area_thresh = all_a[idx_a] if all_a else DEFAULT_AREA_ACTIVE_THRESHOLD
    return {
        "activation_threshold": round(act_thresh, 4),
        "area_active_threshold": round(area_thresh, 4),
    }
