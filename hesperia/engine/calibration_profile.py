# HESPERIA — governed calibration profiles (VERSION-bound).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hesperia.system.version import calibration_active_profile_id, calibration_profile_bundle_id

_PROFILES_PATH = Path(__file__).resolve().parents[2] / "assets" / "calibration" / "profiles_v1.json"
_PROFILE_DOC_CACHE: dict[str, Any] | None = None


def _profile_path_for_bundle() -> Path:
    _ = calibration_profile_bundle_id()
    return _PROFILES_PATH


def _load_profiles_doc(path: Path | str | None = None) -> dict[str, Any]:
    global _PROFILE_DOC_CACHE
    p = Path(path) if path is not None else _profile_path_for_bundle()
    if p == _PROFILES_PATH and _PROFILE_DOC_CACHE is not None:
        return dict(_PROFILE_DOC_CACHE)
    if not p.is_file():
        raise FileNotFoundError(f"calibration profiles missing: {p}")
    doc = json.loads(p.read_text(encoding="utf-8"))
    if p == _PROFILES_PATH:
        _PROFILE_DOC_CACHE = dict(doc)
    return dict(doc)


def load_calibration_profile(
    name: str | None = None,
    *,
    profiles_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    Return resolved profile dict (alpha, beta, gamma, delta, dt, ...).

    ``name`` defaults to ``VERSION.yaml`` ``calibration.active_profile``.
    """
    doc = _load_profiles_doc(profiles_path)
    bundle = str(doc.get("bundle_version", ""))
    expected = calibration_profile_bundle_id()
    if bundle and expected and bundle != expected:
        raise RuntimeError(
            f"profiles bundle_version {bundle!r} != VERSION calibration.profile_bundle {expected!r}"
        )
    prof_name = name or calibration_active_profile_id()
    profiles = doc.get("profiles") or {}
    if prof_name not in profiles:
        raise RuntimeError(f"Unknown calibration profile {prof_name!r} in profiles file")
    raw = dict(profiles[prof_name])
    if raw.get("alias_of"):
        base = str(raw["alias_of"])
        if base not in profiles:
            raise RuntimeError(f"alias_of {base!r} missing")
        raw = dict(profiles[base])
    raw.pop("alias_of", None)
    return raw


def semantic_field_params_from_profile(
    name: str | None = None,
    *,
    profiles_path: Path | str | None = None,
):
    """Build ``SemanticFieldParams`` from governed profile."""
    from hesperia.extensions.dynamics.equations import SemanticFieldParams

    p = load_calibration_profile(name, profiles_path=profiles_path)
    return SemanticFieldParams(
        alpha=float(p["alpha"]),
        beta=float(p["beta"]),
        gamma=float(p["gamma"]),
        delta=float(p["delta"]),
        dt=float(p["dt"]),
        epsilon=float(p.get("epsilon", 1e-6)),
        tau=float(p.get("tau", 1e-6)),
        clip_mode=bool(p.get("clip_mode", True)),
    )


__all__ = [
    "load_calibration_profile",
    "semantic_field_params_from_profile",
]
