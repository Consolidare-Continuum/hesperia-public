# HESPERIA — LEVEL 15 Propagation weights loader (graph calibration)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""
Load spec/propagation_weights.yaml for zone weights, bridge weight, decay.
Ensures reproducible propagation; replaces hardcoded heuristics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_SPEC_DIR = Path(__file__).resolve().parents[2] / "spec"
_DEFAULT_PATH = _SPEC_DIR / "propagation_weights.yaml"

# Defaults (match previous heuristics if file missing)
DEFAULT_ZONE_WEIGHTS = {
    "center_to_inner": 0.25,
    "inner_to_middle": 0.18,
    "middle_to_inner": 0.18,
    "middle_to_outer": 0.12,
    "outer_to_middle": 0.12,
}
DEFAULT_BRIDGE_WEIGHT = 0.22
DEFAULT_DECAY_FACTOR = 1.0


def load_propagation_weights(path: Path | str | None = None) -> dict[str, Any]:
    """
    Загрузить spec/propagation_weights.yaml.
    Возвращает dict: zone_weights, bridge_weight, decay_factor, concept_to_family_multiplier.
    При отсутствии файла — константы по умолчанию.
    """
    p = Path(path) if path is not None else _DEFAULT_PATH
    if not p.exists():
        return {
            "zone_weights": dict(DEFAULT_ZONE_WEIGHTS),
            "bridge_weight": DEFAULT_BRIDGE_WEIGHT,
            "decay_factor": DEFAULT_DECAY_FACTOR,
            "concept_to_family_multiplier": 1.0,
        }
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    zw = data.get("zone_weights") or {}
    return {
        "zone_weights": {
            "center_to_inner": float(zw.get("center_to_inner", DEFAULT_ZONE_WEIGHTS["center_to_inner"])),
            "inner_to_middle": float(zw.get("inner_to_middle", DEFAULT_ZONE_WEIGHTS["inner_to_middle"])),
            "middle_to_inner": float(zw.get("middle_to_inner", DEFAULT_ZONE_WEIGHTS["middle_to_inner"])),
            "middle_to_outer": float(zw.get("middle_to_outer", DEFAULT_ZONE_WEIGHTS["middle_to_outer"])),
            "outer_to_middle": float(zw.get("outer_to_middle", DEFAULT_ZONE_WEIGHTS["outer_to_middle"])),
        },
        "bridge_weight": float(data.get("bridge_weight", DEFAULT_BRIDGE_WEIGHT)),
        "decay_factor": float(data.get("decay_factor", DEFAULT_DECAY_FACTOR)),
        "concept_to_family_multiplier": float(data.get("concept_to_family_multiplier", 1.0)),
    }


def get_within_area_spread(weights: dict[str, Any] | None = None) -> list[tuple[str, str, float]]:
    """Return [(source_zone, target_zone, coefficient), ...] for propagation. Uses loaded weights if provided."""
    w = weights or load_propagation_weights()
    zw = w.get("zone_weights") or DEFAULT_ZONE_WEIGHTS
    return [
        ("center", "inner_ring", zw.get("center_to_inner", 0.25)),
        ("inner_ring", "middle_ring", zw.get("inner_to_middle", 0.18)),
        ("middle_ring", "inner_ring", zw.get("middle_to_inner", 0.18)),
        ("middle_ring", "outer_ring", zw.get("middle_to_outer", 0.12)),
        ("outer_ring", "middle_ring", zw.get("outer_to_middle", 0.12)),
    ]


def get_bridge_weight(weights: dict[str, Any] | None = None) -> float:
    """Return bridge weight. Uses loaded weights if provided."""
    w = weights or load_propagation_weights()
    return float(w.get("bridge_weight", DEFAULT_BRIDGE_WEIGHT))
