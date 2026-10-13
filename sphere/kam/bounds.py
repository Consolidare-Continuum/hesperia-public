# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""Load versioned KAM perturbation bounds (Ethan-owned; SPEC defaults fallback)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Mapping

from sphere.kam.flags import kam_bounds_path

PathSurvivalUses = Literal["SISR_min", "SISR_mean"]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_BOUNDS = _REPO_ROOT / "assets" / "data" / "kam" / "kam_perturbation_bounds_v01.json"

_SPEC_DEFAULTS: dict[str, Any] = {
    "version": "spec-v01-defaults",
    "schema": "hesperia.kam_perturbation_bounds.v01",
    "epsilon_shadow": 0.05,
    "epsilon_edge": 0.02,
    "epsilon_bias": 0.05,
    "tau_path": 0.7,
    "tau_crit": 0.1,
    "path_survival_uses": "SISR_min",
    "band_thresholds": {
        "structurally_robust_min": 0.75,
        "conditionally_stable_min": 0.45,
    },
    "active_perturbations_default": ["P2_shadow_context", "P3_edge_weight_epsilon"],
}


@dataclass(frozen=True, slots=True)
class KamBounds:
    """Versioned ε/τ/band knobs — not theorem constants."""

    version: str
    epsilon_shadow: float
    epsilon_edge: float
    epsilon_bias: float
    tau_path: float
    tau_crit: float
    path_survival_uses: PathSurvivalUses
    structurally_robust_min: float
    conditionally_stable_min: float
    active_perturbations_default: tuple[str, ...]
    source_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "epsilon_shadow": self.epsilon_shadow,
            "epsilon_edge": self.epsilon_edge,
            "epsilon_bias": self.epsilon_bias,
            "tau_path": self.tau_path,
            "tau_crit": self.tau_crit,
            "path_survival_uses": self.path_survival_uses,
            "band_thresholds": {
                "structurally_robust_min": self.structurally_robust_min,
                "conditionally_stable_min": self.conditionally_stable_min,
            },
            "active_perturbations_default": list(self.active_perturbations_default),
            "source_path": self.source_path,
        }


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _parse_bounds(raw: Mapping[str, Any], *, source_path: str | None) -> KamBounds:
    bands = raw.get("band_thresholds") or {}
    uses = str(raw.get("path_survival_uses", "SISR_min")).strip()
    if uses not in ("SISR_min", "SISR_mean"):
        uses = "SISR_min"
    active = raw.get("active_perturbations_default") or [
        "P2_shadow_context",
        "P3_edge_weight_epsilon",
    ]
    return KamBounds(
        version=str(raw.get("version") or "spec-v01-defaults"),
        epsilon_shadow=_clamp01(float(raw.get("epsilon_shadow", 0.05))),
        epsilon_edge=_clamp01(float(raw.get("epsilon_edge", 0.02))),
        epsilon_bias=_clamp01(float(raw.get("epsilon_bias", 0.05))),
        tau_path=_clamp01(float(raw.get("tau_path", 0.7))),
        tau_crit=_clamp01(float(raw.get("tau_crit", 0.1))),
        path_survival_uses=uses,  # type: ignore[arg-type]
        structurally_robust_min=_clamp01(float(bands.get("structurally_robust_min", 0.75))),
        conditionally_stable_min=_clamp01(float(bands.get("conditionally_stable_min", 0.45))),
        active_perturbations_default=tuple(str(x) for x in active),
        source_path=source_path,
    )


@lru_cache(maxsize=4)
def load_kam_bounds(path: str | None = None) -> KamBounds:
    """Load bounds JSON; fall back to SPEC-v01 defaults with version tag."""
    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    env_path = kam_bounds_path()
    if env_path is not None:
        candidates.append(env_path)
    candidates.append(_DEFAULT_BOUNDS)

    for cand in candidates:
        try:
            if cand.is_file():
                data = json.loads(cand.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return _parse_bounds(data, source_path=str(cand))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return _parse_bounds(_SPEC_DEFAULTS, source_path=None)


def clear_bounds_cache() -> None:
    load_kam_bounds.cache_clear()
