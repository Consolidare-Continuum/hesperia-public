"""
Central contradiction calibration profile (Task 11): one surface for tunable transforms.

Structural invariants (ontology, contract field names, mode enum names) are not
represented here — only bounded transform weights and governance thresholds.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

REQUIRED_TOP_LEVEL_KEYS = frozenset(
    {
        "version",
        "profile_name",
        "activation",
        "uncertainty",
        "negation_inhibition",
        "family",
        "topology",
        "feedback",
        "release_gating",
        "constraints",
    }
)

ALLOWED_PRESSURE_MODES = frozenset({"max", "sum"})

# Keys that must never appear (reserved / future abuse).
FORBIDDEN_KEYS_ANYWHERE = frozenset(
    {
        "override_contract",
        "rename_fields",
        "skip_raw_effective_split",
        "calibrate_ontology",
    }
)


def _deep_forbidden_scan(obj: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            ks = str(k)
            if ks in FORBIDDEN_KEYS_ANYWHERE:
                hits.append(f"{path}.{ks}" if path else ks)
            hits.extend(_deep_forbidden_scan(v, f"{path}.{ks}" if path else ks))
    elif isinstance(obj, list):
        for i, it in enumerate(obj):
            hits.extend(_deep_forbidden_scan(it, f"{path}[{i}]"))
    return hits


def get_default_contradiction_calibration() -> dict[str, Any]:
    """Safe built-in default (identity transforms, governance thresholds as shipped)."""
    return {
        "version": "v0.5.8",
        "profile_name": "cb-contradiction-default",
        "activation": {
            "pressure_normalization_mode": "max",
            "pressure_smooth_compression": 1.0,
            "family_contradiction_influence": 1.0,
            "area_contradiction_influence": 1.0,
            "dynamic_inhibition_influence": 1.0,
        },
        "uncertainty": {
            "confidence_floor": 0.0,
            "confidence_sensitivity": 1.0,
            "fuzzy_penalty_influence": 1.0,
            "ambiguity_penalty_influence": 1.0,
        },
        "negation_inhibition": {
            "negated_opposition_activation_weight": 1.0,
            "inhibited_opposition_activation_weight": 1.0,
            "inhibited_opposition_latent_weight": 1.0,
            "coactive_opposition_latent_weight": 1.0,
        },
        "family": {
            "family_fragmentation_influence": 1.0,
            "family_bridge_influence": 1.0,
            "same_family_conflict_diagonal_weight": 1.0,
        },
        "topology": {
            "segment_contradiction_influence": 1.0,
            "momentum_attenuation_influence": 1.0,
            "transition_pressure_influence": 1.0,
        },
        "feedback": {
            "token_risk_influence": 1.0,
            "concept_risk_influence": 1.0,
            "pair_risk_influence": 1.0,
            "recurrence_influence": 1.0,
        },
        "release_gating": {
            "pass_threshold": 0.85,
            "qualified_pass_threshold": 0.65,
        },
        "constraints": {
            "allow_negative_influence": False,
            "max_global_influence": 2.0,
            "require_trace_visible_config": True,
        },
    }


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _check_numeric_influences(
    payload: dict[str, Any],
    allow_negative: bool,
    max_inf: float,
) -> list[str]:
    errs: list[str] = []
    for sec in (
        "activation",
        "uncertainty",
        "negation_inhibition",
        "family",
        "topology",
        "feedback",
    ):
        block = payload.get(sec) or {}
        if not isinstance(block, Mapping):
            errs.append(f"section_not_mapping:{sec}")
            continue
        for k, v in block.items():
            if k == "pressure_normalization_mode":
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                errs.append(f"non_numeric:{sec}.{k}")
                continue
            if not allow_negative and fv < 0.0:
                errs.append(f"negative_influence:{sec}.{k}")
            if abs(fv) > max_inf + 1e-9:
                errs.append(f"exceeds_max_global_influence:{sec}.{k}")
    return errs


def validate_contradiction_calibration(payload: Any) -> dict[str, Any]:
    """
    Validate a calibration profile. Returns ``{"ok": bool, "errors": [...], "normalized": dict}``.
    """
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {"ok": False, "errors": ["payload_not_mapping"], "normalized": {}}

    extra = set(payload.keys()) - REQUIRED_TOP_LEVEL_KEYS
    if extra:
        errors.append(f"unknown_top_level_keys:{sorted(extra)}")

    missing = REQUIRED_TOP_LEVEL_KEYS - set(payload.keys())
    if missing:
        errors.append(f"missing_keys:{sorted(missing)}")

    forbidden = _deep_forbidden_scan(payload)
    if forbidden:
        errors.append(f"forbidden_keys_present:{forbidden}")

    ver = str(payload.get("version") or "").strip()
    if not ver:
        errors.append("missing_version")
    pname = str(payload.get("profile_name") or "").strip()
    if not pname:
        errors.append("missing_profile_name")

    act = payload.get("activation") or {}
    if isinstance(act, Mapping):
        mode = str(act.get("pressure_normalization_mode") or "max").strip()
        if mode not in ALLOWED_PRESSURE_MODES:
            errors.append(f"invalid_pressure_normalization_mode:{mode}")

    rg = payload.get("release_gating") or {}
    if isinstance(rg, Mapping):
        try:
            pt = float(rg.get("pass_threshold", 0.85))
            qpt = float(rg.get("qualified_pass_threshold", 0.65))
        except (TypeError, ValueError):
            errors.append("release_gating_thresholds_non_numeric")
            pt, qpt = 1.0, 0.0
        if not (0.0 <= qpt <= pt <= 1.0):
            errors.append("release_gating_threshold_inversion_or_oob")

    cons = payload.get("constraints") or {}
    allow_neg = bool(cons.get("allow_negative_influence", False)) if isinstance(cons, Mapping) else False
    try:
        max_inf = float(cons.get("max_global_influence", 2.0)) if isinstance(cons, Mapping) else 2.0
    except (TypeError, ValueError):
        max_inf = 2.0
        errors.append("constraints.max_global_influence_invalid")

    errors.extend(_check_numeric_influences(payload if isinstance(payload, Mapping) else {}, allow_neg, max_inf))

    ok = len(errors) == 0
    normalized = dict(payload) if isinstance(payload, Mapping) else {}
    return {"ok": ok, "errors": errors, "normalized": normalized}


def load_contradiction_calibration(path_or_payload: str | Path | Mapping[str, Any] | None) -> dict[str, Any]:
    """
    Load calibration from a JSON path, inline mapping, or None (defaults).

    Merges with :func:`get_default_contradiction_calibration` for any missing sections
    so runtime always has a complete profile.
    """
    base = get_default_contradiction_calibration()
    if path_or_payload is None:
        return base

    if isinstance(path_or_payload, (str, Path)):
        p = Path(path_or_payload)
        if not p.is_file():
            raise FileNotFoundError(str(p))
        with open(p, encoding="utf-8") as fh:
            raw = json.load(fh)
    elif isinstance(path_or_payload, Mapping):
        raw = dict(path_or_payload)
    else:
        raise TypeError("path_or_payload must be path-like or mapping")

    merged: dict[str, Any] = {**base}
    for k, v in raw.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, Mapping):
            merged[k] = {**base[k], **dict(v)}
        else:
            merged[k] = v

    val = validate_contradiction_calibration(merged)
    if not val["ok"]:
        raise ValueError("invalid contradiction calibration: " + "; ".join(val["errors"]))
    return val["normalized"]


def calibration_payload_sha256(payload: Mapping[str, Any]) -> str:
    """Stable hash of canonical JSON (sorted keys) for audit."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _flatten_leaves(prefix: str, obj: Any, out: dict[str, Any]) -> None:
    if not isinstance(obj, Mapping):
        if prefix:
            out[prefix] = obj
        return
    for k, v in sorted(obj.items()):
        kk = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, Mapping):
            _flatten_leaves(kk, v, out)
        else:
            out[kk] = v


def build_calibration_usage_trace(
    active: Mapping[str, Any],
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, bool]:
    """
    For each leaf numeric / string field in the profile, True if value differs from the default profile.
    """
    d = defaults or get_default_contradiction_calibration()
    af: dict[str, Any] = {}
    bf: dict[str, Any] = {}
    _flatten_leaves("", dict(active), af)
    _flatten_leaves("", dict(d), bf)
    keys = set(af.keys()) | set(bf.keys())
    return {k: af.get(k) != bf.get(k) for k in sorted(keys)}


def build_calibration_snapshot(
    payload: Mapping[str, Any],
    source_path: str | None,
    active_sections: list[str] | None = None,
) -> dict[str, Any]:
    secs = active_sections or [
        "activation",
        "uncertainty",
        "negation_inhibition",
        "family",
        "topology",
        "feedback",
        "release_gating",
    ]
    return {
        "profile_name": str(payload.get("profile_name", "")),
        "version": str(payload.get("version", "")),
        "path": source_path or "",
        "active_sections": secs,
        "sha256": calibration_payload_sha256(payload),
    }


def default_calibration_path() -> Path:
    """Canonical profile path under repo ``assets/`` (package ``hesperia/hesperia``)."""
    here = Path(__file__).resolve()
    # .../hesperia/hesperia/hesperia/extensions/triz/thisfile -> parents[3] == repo package root
    repo_pkg = here.parents[3]
    return (
        repo_pkg
        / "assets"
        / "data"
        / "engine_dynamics_v060"
        / "tfp"
        / "contradiction_calibration_v1.json"
    )
