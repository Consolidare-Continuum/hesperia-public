"""Build session_inspector_v1 from live TFP analyze / interpret JSON (HES-TFP-100-78)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .bundle import build_session_inspector_v1
from .constants import SESSION_INSPECTOR_SCHEMA_VERSION


def _areas_from_analyze(body: dict[str, Any]) -> dict[str, float]:
    ms = body.get("multiscale_signals") or {}
    av = ms.get("area_activation_vector") or body.get("area_activation_vector")
    if isinstance(av, list) and av:
        return {f"A{i+1}": float(av[i]) for i in range(min(12, len(av)))}
    # interpret-shaped
    eng = body.get("router_envelope", {}).get("engine_trace") or body.get("engine_trace") or {}
    out: dict[str, float] = {}
    for step in eng.get("trace") or []:
        aid = str(step.get("area_id") or "")
        if aid:
            out[aid] = float(step.get("activation") or 0.0)
    return out


def build_session_inspector_v1_from_analyze_json(
    analyze_body: dict[str, Any],
    *,
    session_id: str = "live-analyze",
    interpret_body: dict[str, Any] | None = None,
    profile_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map /analyze (+ optional /product/interpret) into session_inspector_v1."""
    areas = _areas_from_analyze(analyze_body)
    families: dict[str, float] = {}
    ms = analyze_body.get("multiscale_signals") or {}
    fav = ms.get("family_activation_vector") or []
    if isinstance(fav, list):
        for i, v in enumerate(fav[:48]):
            families[f"F{i:03d}"] = float(v)

    meta = {
        "session_id": session_id,
        "source": "analyze_api",
        "source_file": f"{session_id}.json",
        "source_label": session_id,
        "modules_executed": ["tfp.v1"],
        "module_versions": {"tfp.v1": "live"},
        "calibration_dict_pack": None,
        "analyze_profile": profile_meta or analyze_body.get("analyze_profile_meta") or {},
        "schema_hint": SESSION_INSPECTOR_SCHEMA_VERSION,
        "disclaimer_footer": (
            "This output is a computational artifact from the Hesperia analysis engine. "
            "It is not medical advice, diagnosis, or treatment."
        ),
    }
    if interpret_body is not None:
        meta["interpret_schema"] = interpret_body.get("schema")
        meta["hspr_index"] = interpret_body.get("hspr_index")
        meta["layer9_present"] = "layer9_logic" in interpret_body

    # hoist profile fields for Pane B (HES-TFP-100-80)
    pm = meta.get("analyze_profile") if isinstance(meta.get("analyze_profile"), dict) else {}
    parameters: dict[str, Any] = {
        "areas": areas,
        "families": families,
        "metrics": {
            "hspr_index": (ms.get("hspr_index") if ms else None)
            or ((interpret_body or {}).get("hspr_index")),
            "governance": (
                ((interpret_body or {}).get("router_envelope") or {})
                .get("engine_trace", {})
                .get("governance")
            ),
        },
        "modules": {
            "tfp": {
                "v1": {
                    "analyze_extended": {
                        "grain": pm.get("area_math") or pm.get("grain") or pm.get("HESPERIA_AREA_MATH_GRAIN"),
                        "pack": pm.get("pack_areas") or pm.get("pack"),
                        "dict_mode": pm.get("dict_mode") or pm.get("HESPERIA_TFP_DICT_MODE"),
                        "structure": pm.get("structure_map") or pm.get("structure"),
                        "profile": pm,
                    }
                }
            }
        },
        "tfp_profile": {
            "grain": pm.get("area_math") or pm.get("grain"),
            "pack": pm.get("pack_areas") or pm.get("pack"),
            "dict_mode": pm.get("dict_mode"),
            "structure": pm.get("structure_map") or pm.get("structure"),
        },
    }
    # fill from analyze_profile_meta flat keys if present on body
    apm = analyze_body.get("analyze_profile_meta") or analyze_body.get("meta") or {}
    if isinstance(apm, dict):
        tp = parameters["tfp_profile"]
        for src, dst in (
            ("area_math", "grain"),
            ("pack_areas", "pack"),
            ("dict_mode", "dict_mode"),
            ("structure_map", "structure"),
        ):
            if tp.get(dst) is None and apm.get(src) is not None:
                tp[dst] = apm.get(src)
        parameters["modules"]["tfp"]["v1"]["analyze_extended"].update(
            {k: tp[k] for k in ("grain", "pack", "dict_mode", "structure") if tp.get(k) is not None}
        )

    iteration = {
        "order": 0,
        "iteration_id": f"{session_id}-0",
        "parameters": parameters,
        "sentences": [
            {
                "id": "s0",
                "text": str(
                    analyze_body.get("input_text")
                    or (interpret_body or {}).get("interpretation", {}).get("structural_summary")
                    or "(analyze)"
                )[:2000],
            }
        ],
        "audit": {
            "planes": {
                "analyze_keys": sorted(list(analyze_body.keys()))[:40],
            }
        },
    }
    artifact = {"meta": meta, "iterations": [iteration]}
    return build_session_inspector_v1(artifact)


def fetch_analyze_json(url: str, text: str, timeout: float = 60.0) -> dict[str, Any]:
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/analyze",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_fixture_from_analyze(
    analyze_body: dict[str, Any],
    fixture_path: Path,
    *,
    session_id: str,
    interpret_body: dict[str, Any] | None = None,
) -> Path:
    bundle = build_session_inspector_v1_from_analyze_json(
        analyze_body, session_id=session_id, interpret_body=interpret_body
    )
    fixture_path = Path(fixture_path)
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return fixture_path
