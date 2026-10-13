# HESPERIA — Analyze API profile (default vs TFP side-by-side).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Side-by-side analyze profiles — default core vs TFP Class B lane.

``HESPERIA_ANALYZE_PROFILE=default|tfp`` (default: ``default``).

TFP profile does **not** merge into sealed core physics. It selects the
operational pack (area-math grain 10), enables structural DLCR against the
full ``dict_*_tfp*`` merge stack, and announces the lane on /health and
response meta. Run on a **separate port/unit** so ``:18880`` stays grain-12 core.
"""

from __future__ import annotations

import os
from typing import Any, Literal

AnalyzeProfile = Literal["default", "tfp"]

_ENV = "HESPERIA_ANALYZE_PROFILE"
_TRUTHY = ("1", "true", "yes", "on")


def resolve_analyze_profile(*, explicit: str | None = None) -> AnalyzeProfile:
    raw = (explicit if explicit is not None else os.environ.get(_ENV, "default") or "default")
    s = str(raw).strip().lower()
    if s in ("tfp", "tfp_v1", "class_b_tfp"):
        return "tfp"
    if s in ("default", "core", "class_a", ""):
        return "default"
    raise ValueError(f"invalid {_ENV}={raw!r}; expected default|tfp")


def apply_analyze_profile_defaults(*, profile: AnalyzeProfile | None = None) -> AnalyzeProfile:
    """
    Apply env defaults for the selected profile (process-local).

    Explicit ``HESPERIA_AREA_MATH_GRAIN`` / ``HESPERIA_CALIB_DICT_VERSION`` /
    ``HESPERIA_DLCR_STRUCTURAL`` win when already set.

    TFP MVP: prefer **full** ``dict_*_tfp*`` stack. Auto-pins the sealed ACB
    calibration pack (``v0_6_0_clr_v052_5`` as of 2026-08-18 — operator-confirmed
    current seal: Dict B 283 concepts, Dict A 10155 token entries -> 135 B ids,
    Dict C 24000 phrases -> 212 B ids via links.jsonl) instead of leaving
    ``HESPERIA_CALIB_DICT_VERSION`` unset, which previously silently fell through
    to ``assets/data/engine_dynamics_v060/dict_{a,b}/*`` — a much smaller fallback
    stack, not itself "tiny" like ``v0_tfp_cal_wave_002`` but still well short of
    the sealed pack. Empirically verified (Chiron, 2026-08-18) on two RU clinical
    test statements: 2->6 and 4->7 concept_weights entries, lexical_hits_accepted
    2->10 and 3->12, once this pin is applied. Still an ``if not already set``
    default, not a hard pin — an explicit ``HESPERIA_CALIB_DICT_VERSION`` still wins.
    """
    p = profile if profile is not None else resolve_analyze_profile()
    if p == "tfp":
        if not (os.environ.get("HESPERIA_AREA_MATH_GRAIN") or "").strip():
            os.environ["HESPERIA_AREA_MATH_GRAIN"] = "10"
        if not (os.environ.get("HESPERIA_TFP_MODULE_SEALED") or "").strip():
            os.environ["HESPERIA_TFP_MODULE_SEALED"] = "0"
        if not (os.environ.get("HESPERIA_DLCR_STRUCTURAL") or "").strip():
            # Sidecar TFP dicts onto structural analyze (requires capabilities internal.dlcr).
            os.environ["HESPERIA_DLCR_STRUCTURAL"] = "1"
        if not (os.environ.get("HESPERIA_TFP_DICT_MODE") or "").strip():
            os.environ["HESPERIA_TFP_DICT_MODE"] = "full_stack"
        if not (os.environ.get("HESPERIA_CALIB_DICT_VERSION") or "").strip():
            os.environ["HESPERIA_CALIB_DICT_VERSION"] = "v0_6_0_clr_v052_5"
    return p


def analyze_profile_meta(*, profile: AnalyzeProfile | None = None) -> dict[str, Any]:
    from core.projection.area_math_grain import area_math_classifier_meta, area_math_totals

    p = profile if profile is not None else resolve_analyze_profile()
    totals = area_math_totals()
    meta: dict[str, Any] = {
        "analyze_profile": p,
        "class": "B" if p == "tfp" else "A",
        "branch": "tfp" if p == "tfp" else "default",
        "area_math": area_math_classifier_meta(),
        "pack_areas": totals["areas"],
        "pack_families": totals["families"],
        "geometry_areas_lock": totals["geometry_areas_lock"],
        "geometry_families_lock": totals["geometry_families_lock"],
        "note": (
            "TFP Class B lane — operational pack 10/240; geometry lock remains 12/288"
            if p == "tfp"
            else "Default Class A core lane — grain 12 / 288 families"
        ),
    }
    if p == "tfp":
        meta["instructor"] = {
            "path": "analyze_then_interpret",
            "api_and_agent": "same",
            "faces": ["/analyze", "/product/interpret"],
        }
        meta["structure_map"] = {
            "area": "assets/specs/canon/area_structure_tfp.yaml",
            "families": "assets/specs/canon/families_structure_tfp.yaml",
        }
        meta["dict_mode"] = (os.environ.get("HESPERIA_TFP_DICT_MODE") or "full_stack").strip()
        meta["dlcr_structural"] = (os.environ.get("HESPERIA_DLCR_STRUCTURAL") or "").strip().lower() in _TRUTHY
        meta["calib_dict_version"] = (os.environ.get("HESPERIA_CALIB_DICT_VERSION") or "").strip() or None
        meta["corpus_snapshot_id"] = os.environ.get("HESPERIA_TFP_CORPUS_SNAPSHOT_ID") or "chroma2_tfp_ru_live"
        meta["corpus_home"] = "chroma-2_colombo_library"
        meta["product_tfp_mount"] = "document_only_no_/product/tfp"
    return meta


def attach_analyze_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach profile meta without mutating caller dict identity when possible."""
    out = dict(payload)
    out["analyze_profile_meta"] = analyze_profile_meta()
    out["analyze_profile"] = out["analyze_profile_meta"]["analyze_profile"]
    return out
