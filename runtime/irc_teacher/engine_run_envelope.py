"""Hesperia 0.6.3 — engine run envelope builder (H063-14..18)."""
from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path
from typing import Any, Mapping

from runtime.irc_teacher.teacher_packet import serialize_teacher_packet


def _repo_root() -> Path:
    env = os.environ.get("HESPERIA_ROOT") or os.environ.get("HESPERIA_REPO_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _integration_root() -> Path | None:
    env = os.environ.get("TERSAGOR_ROOT") or os.environ.get("HESPERIA_INTEGRATION_ROOT")
    return Path(env) if env else None


def _git_sha(path: Path | None) -> str | None:
    if path is None or not path.is_dir():
        return None
    try:
        out = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _roads_from_engine(engine: Mapping[str, Any]) -> list[dict[str, Any]]:
    trace = engine.get("propagation_trace") or []
    roads: list[dict[str, Any]] = []
    if isinstance(trace, list):
        for i, step in enumerate(trace):
            if isinstance(step, dict):
                roads.append({"hop": i, **step})
    gtp = engine.get("gtp_coherence") or {}
    if isinstance(gtp, dict) and gtp.get("path_ids"):
        roads.append({"gtp_path_ids": gtp.get("path_ids")})
    return roads


def _corpus_activations(engine: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    inv = engine.get("invariant_activation") or {}
    concepts = inv.get("concepts") if isinstance(inv, dict) else None
    if isinstance(concepts, dict):
        for cid, row in concepts.items():
            if not isinstance(row, dict):
                continue
            out.append(
                {
                    "concept_id": cid,
                    "observed": row.get("observed", row.get("activation")),
                    "expected": row.get("expected"),
                }
            )
    return out


def _parameters_block(ksi: Mapping[str, Any]) -> dict[str, Any]:
    phi = ksi.get("phi_trace") or {}
    edges: list[dict[str, Any]] = []
    if isinstance(phi, dict):
        for key, row in phi.items():
            if isinstance(row, dict):
                edges.append({"edge": key, **row})
    return {
        "W_e": edges,
        "ksi_config_ref": os.environ.get(
            "HESPERIA_KSI_CONFIG", "assets/data/ksi/ksi_config_v01.json"
        ),
    }


def build_engine_run_envelope(
    *,
    text_ru: str,
    correlation_id: str,
    hybrid_output: Any,
    lang: str = "ru",
    input_kind: str = "tfp_scientific_statement",
) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    engine_result = getattr(hybrid_output, "engine_result", None) or {}
    ksi_block: dict[str, Any] = {}
    if hasattr(hybrid_output, "context_package") and hybrid_output.context_package:
        pkg = hybrid_output.context_package
        if isinstance(pkg, dict):
            ksi_block = pkg.get("ksi") or {}
    if not ksi_block and isinstance(engine_result, dict):
        ksi_block = engine_result.get("ksi") or {}

    engine_payload: dict[str, Any] = {
        "hesperia_ref": _git_sha(_repo_root()),
        "integration_host_ref": _git_sha(_integration_root()),
        "propagation_trace": engine_result.get("propagation_trace") if isinstance(engine_result, dict) else [],
        "areas": engine_result.get("areas") if isinstance(engine_result, dict) else {},
        "families": engine_result.get("families") if isinstance(engine_result, dict) else {},
        "tfp_vector": engine_result.get("tfp_vector") if isinstance(engine_result, dict) else {},
        "invariant_activation": engine_result.get("invariant_activation") if isinstance(engine_result, dict) else {},
        "interior_pov": getattr(hybrid_output, "interior_pov", None),
        "gtp_coherence": getattr(hybrid_output, "gtp_coherence", None),
        "corpus_activations": _corpus_activations(engine_result if isinstance(engine_result, dict) else {}),
        "roads": _roads_from_engine(engine_result if isinstance(engine_result, dict) else {}),
    }

    return {
        "schema": "hesperia.engine_run_envelope.v063",
        "lang": lang,
        "correlation_id": correlation_id,
        "run_id": run_id,
        "input": {"text_ru": text_ru, "kind": input_kind},
        "engine": engine_payload,
        "ksi": ksi_block if isinstance(ksi_block, dict) else {},
        "parameters": _parameters_block(ksi_block if isinstance(ksi_block, dict) else {}),
    }


def build_teacher_request_from_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    ksi = envelope.get("ksi") or {}
    incidents = ksi.get("incidents") or []
    bridges = ksi.get("missing_bridges") or []
    return serialize_teacher_packet(
        session_id=str(envelope.get("run_id", "")),
        iteration_id=str(envelope.get("correlation_id", "")),
        incidents=incidents if isinstance(incidents, list) else [],
        missing_bridges=bridges if isinstance(bridges, list) else [],
    )
