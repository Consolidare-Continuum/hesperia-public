# HESPERIA — Testing-mode parameter envelope (flag-gated; no freeze gates).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Emit ``meta.testing_params`` for LLM/agent testing loops.

Default off via ``HESPERIA_TESTING_PARAMS``. Additive only — public schema stays thin.
No corpus/schema/VERSION freeze required. Honesty statuses: live | stub | uncalibrated | partial.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from core.math.core_math import DEFAULT_CONFIG

_TRUTHY = ("1", "true", "yes", "on")
_ENVELOPE_VERSION = "0.1.0"


def testing_params_enabled() -> bool:
    return os.environ.get("HESPERIA_TESTING_PARAMS", "0").strip().lower() in _TRUTHY


def _param(name: str, value: Any, status: str, *, note: str = "") -> dict[str, Any]:
    row: dict[str, Any] = {"name": name, "value": value, "status": status}
    if note:
        row["note"] = note
    return row


def _geometry_params() -> list[dict[str, Any]]:
    from core.projection.area_math_grain import area_math_classifier_meta, area_math_totals
    from core.topology.invariant_catalog import (
        AREAS,
        FAMILIES_PER_AREA,
        HEXES_PER_FAMILY,
        SIDES_PER_HEX,
        TOTAL_FAMILIES,
    )

    totals = area_math_totals()
    meta = area_math_classifier_meta()
    return [
        _param("AREAS", AREAS, "live", note="geometry lock (icosahedral)"),
        _param(
            "area_math_grain",
            totals["grain"],
            "live",
            note=f"classifier switch {meta['switch_env']}=12|10",
        ),
        _param("active_pack_areas", totals["areas"], "live", note="active grain area total"),
        _param("active_pack_families", totals["families"], "live"),
        _param("FAMILIES_PER_AREA", FAMILIES_PER_AREA, "live"),
        _param("TOTAL_FAMILIES", TOTAL_FAMILIES, "live", note="geometry lock"),
        _param("HEXES_PER_FAMILY", HEXES_PER_FAMILY, "live", note="GCS variant may use 251 on some families"),
        _param("SIDES_PER_HEX", SIDES_PER_HEX, "live"),
    ]


def _core_math_params() -> list[dict[str, Any]]:
    # DEFAULT_CONFIG values are live engine defaults; not all are field-calibrated.
    uncalibrated_keys = {
        "k_amb",
        "k_thin",
        "k_disp",
        "k_guard",
        "k_shadow",
        "k_shadow_perturb",
        "w_decay",
        "w_guard_obs",
        "w_shadow_obs",
    }
    out: list[dict[str, Any]] = []
    for key, value in sorted(DEFAULT_CONFIG.items()):
        status = "uncalibrated" if key in uncalibrated_keys else "live"
        out.append(_param(key, value, status, note="core.math.DEFAULT_CONFIG"))
    return out


def _activation_params() -> list[dict[str, Any]]:
    return [
        _param("activation_threshold", 0.01, "live", note="canon activation_calibration.yaml"),
        _param("area_active_threshold", 0.05, "live"),
        _param("center_to_inner", 0.25, "live", note="canon propagation_weights.yaml"),
        _param("inner_to_middle", 0.18, "live"),
        _param("middle_to_outer", 0.12, "live"),
        _param("bridge_weight", 0.22, "live"),
        _param("decay_factor", 1.0, "stub", note="documented no-op multi-hop decay"),
    ]


def _analyze_surface_params(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    keys = (
        "governance",
        "loopability",
        "tension_energy",
        "obstacle_score",
        "dominant_area_id",
        "dominant_family_id",
        "dominant_concept_id",
    )
    rows: list[dict[str, Any]] = []
    for key in keys:
        if key in payload:
            rows.append(_param(f"analyze.{key}", payload.get(key), "live"))
    meta = payload.get("meta") or {}
    if "layer_6" in meta:
        rows.append(
            _param(
                "meta.layer_6",
                "present",
                "partial",
                note="present only when HESPERIA_L6_PERTURBATION=1",
            )
        )
    if "hesperia_metric" in meta:
        rows.append(
            _param(
                "meta.hesperia_metric",
                "present",
                "partial",
                note="present only when HESPERIA_METRIC_EMIT=1",
            )
        )
    return rows


def inventory_default_books_areas() -> dict[str, Any]:
    """Mutable inventory of default books/areas assets — no freeze ceremony."""
    repo = Path(__file__).resolve().parents[2]
    candidates = [
        repo / "assets" / "lexicon" / "curated",
        Path("/data/workspaces/hesperia_mrt/51_DATA__areas_120_authors_books.csv"),
        Path("/data/workspaces/hesperia_mrt/50_DATA__120_books_authors_raw.txt"),
        Path("/data/workspaces/hesperia_mrt/v0.1/areas_120_authors_books.csv"),
    ]
    found: list[dict[str, Any]] = []
    for path in candidates:
        if path.exists():
            found.append(
                {
                    "path": str(path),
                    "kind": "dir" if path.is_dir() else "file",
                    "status": "live",
                }
            )
    book_rows = 0
    for path in candidates:
        if path.is_file() and path.suffix.lower() in {".csv", ".txt"}:
            try:
                book_rows = max(book_rows, sum(1 for _ in path.open(encoding="utf-8", errors="ignore")))
            except OSError:
                pass
    return {
        "freeze": False,
        "mutable": True,
        "assets_found": found,
        "approx_book_map_rows": book_rows,
        "areas": 12,
        "families": 288,
        "note": "default pack inventory for testing; not a frozen corpus snapshot",
        "status": "partial" if found else "stub",
    }


def build_testing_params_block(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    params = (
        _geometry_params()
        + _activation_params()
        + _core_math_params()
        + _analyze_surface_params(payload)
    )
    by_status: dict[str, int] = {}
    for row in params:
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
    return {
        "testing_params_version": _ENVELOPE_VERSION,
        "calibrated_product_claim": False,
        "freeze": False,
        "honesty_policy": {
            "live": "measured or sealed default in current tip",
            "uncalibrated": "numeric default; not field-calibrated",
            "stub": "documented placeholder / no-op",
            "partial": "conditional or incomplete attach",
        },
        "parameter_count": len(params),
        "status_counts": by_status,
        "parameters": params,
        "books_areas_inventory": inventory_default_books_areas(),
    }


def build_testing_retrieval_context() -> dict[str, Any]:
    inv = inventory_default_books_areas()
    return {
        "source": "runtime.services.testing_params_emit",
        "freeze": False,
        "books_areas_inventory": inv,
        "bounding": {
            "status": "partial",
            "note": "inventory attached; full concept↔source↔family↔area retrieval optional",
        },
    }


def attach_testing_params_meta(payload: dict[str, Any]) -> dict[str, Any]:
    if not testing_params_enabled():
        return payload
    out = dict(payload)
    meta = dict(out.get("meta") or {})
    meta["testing_params"] = build_testing_params_block(out)
    out["meta"] = meta
    return out


def attach_testing_params_to_interpret(out: dict[str, Any]) -> dict[str, Any]:
    if not testing_params_enabled():
        return out
    result = dict(out)
    engine = result.get("router_envelope", {}).get("engine_trace") or {}
    block = build_testing_params_block(engine if isinstance(engine, dict) else {})
    result["testing_params"] = block
    envelope = dict(result.get("router_envelope") or {})
    retrieval = dict(envelope.get("retrieval_context") or {})
    if not retrieval:
        retrieval = build_testing_retrieval_context()
        envelope["retrieval_context"] = retrieval
    # Optional label only — not a freeze id.
    if str(envelope.get("corpus_snapshot_id") or "corpus-unset") == "corpus-unset":
        envelope["corpus_snapshot_id"] = "testing-default-pack-mutable"
    result["router_envelope"] = envelope
    return result


def attach_testing_params_to_inquiry(packet: dict[str, Any]) -> dict[str, Any]:
    """Same yield for router-inquire / MCP inquire path."""
    if not testing_params_enabled():
        return packet
    return attach_testing_params_to_interpret(packet)