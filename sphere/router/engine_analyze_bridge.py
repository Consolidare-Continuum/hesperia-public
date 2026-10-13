# HESPERIA — Engine /analyze contract envelope (HES-61-01 Python path).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Build HSPR-01/02 engine_analyze envelope from multiscale internal raw (pre-public projection).

Graduated to sphere 2026-07-31 (was runtime/services/engine_analyze_contract.py) — this is the
one piece of engine-analyze plumbing sphere/router's pre_llm_compiler.py and audit.py actually
need at call time; keeping it in runtime forced sphere to import upward, which the RAD forbids
(tests/architecture/test_layer_dependencies.py::test_sphere_does_not_import_runtime). The old
runtime/services/engine_analyze_contract.py path is kept as a thin re-export shim so no other
caller (runtime/, tools/, tests/) breaks.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.topology.invariant_catalog import FAMILIES_PER_AREA

_CONTRACT_VERSION = "v1.0"


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _area_and_family(global_family_idx: int, area_ids: list[str]) -> tuple[str, str]:
    g = int(global_family_idx)
    area_i = g // FAMILIES_PER_AREA
    if area_i < 0:
        area_i = 0
    if area_i >= len(area_ids):
        area_i = len(area_ids) - 1
    area_id = area_ids[area_i]
    family_id = f"family_{g:03d}"
    return area_id, family_id


def _trace_from_marker_sample(
    sample: list[dict[str, Any]],
    family_activation: list[float],
    area_ids: list[str],
    *,
    overlay_hint: dict[str, Any] | None,
    temp_relation_overlay: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    family_biases = (overlay_hint or {}).get("family_biases") or {}
    temp_boost = 0.0
    if temp_relation_overlay:
        # Minimal HSPR-19: aggregate proposed_strength as advisory boost on trace activations.
        temp_boost = sum(_clamp01(float(o.get("proposed_strength") or 0.0)) for o in temp_relation_overlay) / max(
            1, len(temp_relation_overlay)
        )

    for row in sample:
        lf = row.get("linked_family")
        if lf is None:
            lf = row.get("concept_index", 0)
        try:
            gfi = int(lf)
        except (TypeError, ValueError):
            continue
        area_id, family_id = _area_and_family(gfi, area_ids)
        base_act = 0.5
        if family_activation and 0 <= gfi < len(family_activation):
            base_act = _clamp01(float(family_activation[gfi]))
        bias_key = f"{area_id}:{family_id}"
        bias = family_biases.get(bias_key) or family_biases.get(f"{area_id}:{family_id.split('_', 1)[-1]}")
        if isinstance(bias, dict):
            base_act = _clamp01(
                base_act
                + float(bias.get("prior_boost") or 0.0)
                + float(bias.get("governance_modifier") or 0.0)
                + float(bias.get("contradiction_penalty") or 0.0)
            )
        activation = _clamp01(base_act + temp_boost)
        label = str(row.get("token") or row.get("concept_id") or "concept")
        steps.append(
            {
                "area_id": area_id,
                "family_id": family_id,
                "concept_id": str(row.get("concept_id") or ""),
                "label": label,
                "activation": round(activation, 6),
                "confidence": round(_clamp01(activation * 0.95 + 0.05), 6),
            }
        )
    return steps


def _trace_from_family_vector(family_activation: list[float], area_ids: list[str], limit: int = 8) -> list[dict[str, Any]]:
    ranked = sorted(enumerate(family_activation), key=lambda x: -float(x[1]))[:limit]
    steps: list[dict[str, Any]] = []
    for gfi, act in ranked:
        if float(act) <= 0.0:
            continue
        area_id, family_id = _area_and_family(gfi, area_ids)
        a = _clamp01(float(act))
        steps.append(
            {
                "area_id": area_id,
                "family_id": family_id,
                "concept_id": f"synthetic_family_{gfi:03d}",
                "label": family_id,
                "activation": round(a, 6),
                "confidence": round(a, 6),
            }
        )
    return steps


def _dominants_from_trace(trace: list[dict[str, Any]]) -> tuple[str, str, str]:
    if not trace:
        return ("A1", "family_000", "synthetic_family_000")
    top = max(trace, key=lambda s: float(s.get("activation") or 0.0))
    return (
        str(top.get("area_id") or "A1"),
        str(top.get("family_id") or "family_000"),
        str(top.get("concept_id") or "synthetic_family_000"),
    )


def trace_content_hash(trace: list[dict[str, Any]]) -> str:
    payload = json.dumps(trace, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@lru_cache(maxsize=4)
def _dlcr_dict_b_registry(repo_root_str: str) -> dict[str, dict[str, Any]]:
    """Concept_id -> dict_b row (area_ids/family_ids/preferred_label).

    Same default dict_b path list ``_analyze_internal`` uses (core/engine/lexical_concept/pipeline.py)
    when ``dict_b_paths`` is not explicitly supplied — reused here, not reimplemented, so this stays
    in lockstep with whatever DLCR itself considers canonical.
    """
    from core.engine.lexical_concept.pipeline import _merge_dict_b

    repo_root = Path(repo_root_str)
    base = repo_root / "assets" / "data" / "engine_dynamics_v060"
    db_paths_default = [
        base / "dict_b" / "dict_b_seed.jsonl",
        base / "dict_b" / "dict_b_tfp_ru_v060.jsonl",
        base / "dict_b" / "dict_b_tfp.jsonl",
    ]
    rows = _merge_dict_b([p for p in db_paths_default if p.exists()])
    return {str(r.get("concept_id") or ""): r for r in rows if r.get("concept_id")}


def _trace_from_dlcr_bundle(bundle: dict[str, Any], registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Trace steps from real DLCR concept resolution — one step per matched concept, real labels."""
    weights = bundle.get("concept_weights") or {}
    steps: list[dict[str, Any]] = []
    for concept_id, weight in sorted(weights.items(), key=lambda kv: -float(kv[1])):
        row = registry.get(concept_id) or {}
        area_ids = row.get("area_ids") or ["A?"]
        family_ids = row.get("family_ids") or ["F?"]
        a = _clamp01(float(weight))
        steps.append(
            {
                "area_id": str(area_ids[0]),
                "family_id": str(family_ids[0]),
                "concept_id": concept_id,
                "label": str(row.get("preferred_label") or concept_id),
                "activation": round(a, 6),
                "confidence": round(a, 6),
            }
        )
    return steps


def build_engine_analyze_from_raw(
    raw: dict[str, Any],
    *,
    overlay_hint: dict[str, Any] | None = None,
    temp_relation_overlay: list[dict[str, Any]] | None = None,
    dlcr_bundle: dict[str, Any] | None = None,
    dlcr_registry: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from hesperia.engine.tfp_signal_calibration import AREA_IDS

    ms = raw.get("multiscale_signals") or {}
    diag = raw.get("diagnostics") or {}
    interpret = diag.get("interpretability_trace") or {}
    sample = interpret.get("marker_concept_sample") or []
    fav = [float(x) for x in (ms.get("family_activation_vector") or [])]

    dlcr_trace: list[dict[str, Any]] = []
    if dlcr_bundle is not None:
        dlcr_trace = _trace_from_dlcr_bundle(dlcr_bundle, dlcr_registry or {})

    if dlcr_trace:
        # Real, input-differentiated DLCR concept resolution — strictly preferred over the
        # sealed-core marker-sample/family-vector fallback below when it has something to say.
        trace = dlcr_trace
    else:
        trace = _trace_from_marker_sample(
            sample, fav, AREA_IDS, overlay_hint=overlay_hint, temp_relation_overlay=temp_relation_overlay
        )
        if not trace:
            trace = _trace_from_family_vector(fav, AREA_IDS)

    dom_a, dom_f, dom_c = _dominants_from_trace(trace)

    if dlcr_bundle is not None:
        # DLCR's own tension/loopability/stability are real per-input signal (see run_dlcr_pipeline) —
        # prefer them over the sealed hspr-derived numbers when DLCR ran, empty match or not.
        governance = float(dlcr_bundle.get("stability") or 0.0)
        loopability_val = float(dlcr_bundle.get("loopability") or 0.0)
        tension = float(dlcr_bundle.get("tension") or 0.0)
    else:
        governance = float(ms.get("hspr_index") or 0.0)
        loopability_val = float(ms.get("propagation_strength") or 0.0)
        tension = float(ms.get("contradiction_pressure") or 0.0)

    envelope: dict[str, Any] = {
        "contract_version": _CONTRACT_VERSION,
        "trace": trace,
        "dominant_area_id": dom_a,
        "dominant_family_id": dom_f,
        "dominant_concept_id": dom_c,
        "governance": round(_clamp01(governance), 6),
        "loopability": round(_clamp01(loopability_val), 6),
        "tension_energy": round(_clamp01(tension), 6),
        "obstacle_score": round(_clamp01(1.0 - governance), 6),
        "contradiction_flags": [],
        "weak_signals": [],
        "overlay_hint_applied": bool(overlay_hint),
        "temp_relation_overlay_applied": bool(temp_relation_overlay),
        "trace_content_hash": trace_content_hash(trace),
    }
    if dlcr_bundle is not None:
        envelope["dlcr_source"] = "run_dlcr_pipeline"
        envelope["dlcr_lexical_hits_accepted"] = dlcr_bundle.get("lexical_hits_accepted")
    # Additive KSI-Inspector (Class A core.domain.ksi) — default-off via HESPERIA_KSI_ENABLED.
    # Does not change sealed physics; attaches ``ksi`` only when flag is on.
    if temp_relation_overlay:
        envelope["temp_relation_overlay"] = list(temp_relation_overlay)
    try:
        from core.domain.ksi.pipeline import attach_ksi_to_engine_result

        envelope = attach_ksi_to_engine_result(envelope)
    except Exception:
        # Flag-off path must never fail sealed analyze; on-path errors stay silent empty.
        pass
    return envelope


def run_engine_analyze(
    text: str,
    assets_root: Path | None = None,
    *,
    overlay_hint: dict[str, Any] | None = None,
    temp_relation_overlay: list[dict[str, Any]] | None = None,
    policy_mode: str | None = None,
) -> dict[str, Any]:
    from core.engine.multiscale_product_bridge import build_structural_internal_from_multiscale

    repo_root = Path(__file__).resolve().parents[2]
    assets = assets_root or repo_root / "assets" / "lexicon" / "curated"
    raw = build_structural_internal_from_multiscale(
        text,
        assets,
        policy_mode=policy_mode,
        enable_domain_metrics=False,
        document_id="engine_analyze",
    )

    dlcr_bundle: dict[str, Any] | None = None
    dlcr_registry: dict[str, dict[str, Any]] | None = None
    try:
        from hesperia.system.capabilities import structural_dlcr_allowed

        if structural_dlcr_allowed():
            from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

            dlcr_bundle = run_dlcr_pipeline(text, repo_root=repo_root)
            dlcr_registry = _dlcr_dict_b_registry(str(repo_root))
    except Exception:
        # Same discipline as the KSI attach below: DLCR augmentation is additive-only —
        # any failure here must fall back to the sealed marker-sample/family-vector path,
        # never break run_engine_analyze itself (HESPERIA_DLCR_STRUCTURAL stays default-off
        # on the core/:18880 lane, so this branch is a no-op there regardless).
        dlcr_bundle = None
        dlcr_registry = None

    return build_engine_analyze_from_raw(
        raw,
        overlay_hint=overlay_hint,
        temp_relation_overlay=temp_relation_overlay,
        dlcr_bundle=dlcr_bundle,
        dlcr_registry=dlcr_registry,
    )
