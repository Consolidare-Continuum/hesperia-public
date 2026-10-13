"""T02 — Build `session_inspector_v1` from `run_tfp_file_pipeline` output directory."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bundle import build_session_inspector_v1
from .constants import SESSION_INSPECTOR_SCHEMA_VERSION

_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n+")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _session_row(rows: Any, session_id: str) -> dict[str, Any] | None:
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and str(row.get("session_id")) == session_id:
            return row
    return None


def _sentences_from_text(text: str, *, max_sents: int = 80) -> list[dict[str, Any]]:
    t = (text or "").strip()
    if not t:
        return []
    parts = [p.strip() for p in _SENT_SPLIT.split(t) if p and p.strip()]
    if len(parts) <= 1 and "\n" in t:
        parts = [p.strip() for p in t.split("\n") if p.strip()]
    out: list[dict[str, Any]] = []
    for i, p in enumerate(parts[:max_sents]):
        out.append({"id": f"s{i}", "text": p[:4000], "order": i})
    return out


def build_session_inspector_v1_from_tfp_pipeline_dir(
    bundle_dir: Path | str,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Load artifacts written by ``runtime.pipeline.run_tfp_file_pipeline`` (00–06 JSON) and
    assemble one **session_inspector_v1** bundle with a **single aggregated iteration** (order 0)
    when the pipeline does not emit iteration-sized slices (MVP bridge).

    * ``bundle_dir`` — directory containing ``00_manifest.json`` (optional) and plane files.
    * ``session_id`` — defaults to first entry in manifest ``sessions`` or ``session_ids``.
    """
    root = Path(bundle_dir).resolve()
    manifest = _read_json(root / "00_manifest.json") or {}
    sids = list(manifest.get("sessions") or manifest.get("session_ids") or [])
    sid = session_id or (sids[0] if sids else None)
    if not sid:
        raise ValueError(
            "session_id required when bundle has no 00_manifest.json sessions list "
            f"(dir={root})",
        )

    s02 = _read_json(root / "02_session_tfp_stages.json") or {}
    s01 = _read_json(root / "01_structural_batch.json") or {}
    s04 = _read_json(root / "04_dlcr_full.json") or {}
    s05 = _read_json(root / "05_sealed_multiscale.json") or {}
    s06 = _read_json(root / "06_product_analyze.json") or {}

    stage_row = _session_row(s02.get("session_tfp_stages"), sid)
    struct_row = _session_row(s01.get("structural_batch"), sid)
    dlcr_row = _session_row(s04.get("sessions"), sid)
    sealed_row = _session_row(s05.get("sessions"), sid)
    analyze_row = _session_row(s06.get("sessions"), sid)

    areas_top: dict[str, float] = {}
    if stage_row and isinstance(stage_row.get("areas_top"), dict):
        areas_top = {str(k): float(v) for k, v in stage_row["areas_top"].items() if v is not None}

    structural_payload = (
        (struct_row or {}).get("payload") if isinstance(struct_row, dict) else None
    ) or {}
    hex_map = (sealed_row or {}).get("hex_activation_map") or {}
    extended = (analyze_row or {}).get("extended") or {}

    canonical = ""
    if dlcr_row and not dlcr_row.get("_error"):
        canonical = str(dlcr_row.get("canonical_text") or "")

    sentences = _sentences_from_text(canonical)
    if not sentences:
        sentences = [
            {
                "id": "s0",
                "text": f"(No transcript slice in bundle; session {sid} — synthetic or skipped DLCR.)",
                "order": 0,
            }
        ]

    meta: dict[str, Any] = {
        "run_timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_file": str(manifest.get("run") or root.name),
        "source_label": sid,
        "modules_executed": ["tfp.v1", "tfp_file_pipeline"],
        "module_versions": {"tfp.v1": str(manifest.get("version") or "0.5.6")},
        "calibration_dict_pack": None,
        "pipeline_bundle_dir": root.name,
    }
    if manifest.get("note"):
        meta["note"] = str(manifest["note"])

    parameters: dict[str, Any] = {
        "areas": areas_top,
        "families": {},
        "modules": {
            "tfp.v1": {
                "structural_L1": structural_payload.get("L1") if isinstance(structural_payload, dict) else {},
                "hex_activation_map": hex_map if isinstance(hex_map, dict) else {},
                "analyze_extended": extended if isinstance(extended, dict) else {},
            }
        },
    }

    audit: dict[str, Any] = {
        "iteration": {
            "structural_envelope_ok": bool((struct_row or {}).get("operational_envelope")),
            "sealed_envelope_ok": bool((sealed_row or {}).get("operational_envelope") is not None or sealed_row),
        },
        "by_sentence": {},
        "planes": {
            "01_structural_batch": {"session_id": sid, "payload_keys": list(structural_payload.keys())[:20]}
            if isinstance(structural_payload, dict)
            else {},
            "05_sealed_multiscale": {"hex_total_mass": hex_map.get("total_mass")} if hex_map else {},
            "06_product_analyze": {"attribution_coverage": extended.get("attribution_coverage")}
            if extended
            else {},
        },
    }

    iteration: dict[str, Any] = {
        "iteration_id": "iter_0",
        "order": 0,
        "t_start_ms": 0,
        "t_end_ms": 0,
        "wall_clock_iso": meta["run_timestamp_utc"],
        "parameters": parameters,
        "sentences": sentences,
        "audit": audit,
    }

    artifact: dict[str, Any] = {
        "meta": meta,
        "iterations": [iteration],
    }
    out = build_session_inspector_v1(artifact)
    if out.get("schema_version") != SESSION_INSPECTOR_SCHEMA_VERSION:
        out["schema_version"] = SESSION_INSPECTOR_SCHEMA_VERSION
    return out


def write_session_inspector_fixture(
    bundle_dir: Path | str,
    out_path: Path | str,
    *,
    session_id: str | None = None,
) -> Path:
    """Write JSON fixture for Django ``/inspector/<session_id>/`` (filename stem = session_id)."""
    bundle = build_session_inspector_v1_from_tfp_pipeline_dir(bundle_dir, session_id=session_id)
    sid = str((bundle.get("meta") or {}).get("source_label") or session_id or "session")
    path = Path(out_path)
    if path.is_dir():
        path = path / f"{sid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
