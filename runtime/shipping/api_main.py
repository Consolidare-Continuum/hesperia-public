#!/usr/bin/env python3
# HESPERIA — Shipping API. FastAPI; endpoints: POST /analyze, /compare, /batch-analyze, GET /health.
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""
Sealed API entry point. No internal endpoints. Uses only runtime.services (analysis_service).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

# Optional: license gate at startup (redistribution friction)
def _license_ok() -> bool:
    try:
        from runtime.shipping.license_check import check_license
        return check_license()
    except Exception:
        return True  # If no license module or env bypass, allow


def _runtime_version_fallback() -> str:
    try:
        from hesperia.system.version import get_system_version

        return get_system_version()
    except Exception:
        return "unknown"

# In-memory rate limit: max requests per minute per key (optional)
_RATE: dict[str, list[float]] = {}
_RATE_LIMIT = int(os.environ.get("HESPERIA_RATE_LIMIT", "60"))  # requests per minute
_RATE_WINDOW = 60.0
_MAX_INPUT_CHARS = int(os.environ.get("HESPERIA_MAX_INPUT_CHARS", "10000"))

# FPF-HSR-11: InterpretBody.context_packet — allowlist aligned with what the router pre-LLM
# compiler actually reads off `ctx`, plus `thinking_map_outcome` (extracted and forwarded as its
# own compile_router_envelope() kwarg, not read from ctx directly).
# Ref: governance/ETHAN-FPF-HSR-02-10-ARCHITECTURE-PACKET-2026-07-19.md §FPF-HSR-05.
_CONTEXT_PACKET_ALLOWED_KEYS = frozenset(
    {
        "retrieval",
        "retrieval_context",
        "relation_context",
        "corpus_snapshot_id",
        "calculable",
        "coherence_hints",
        "observability",
        "gtp_current_hex",
        "gtp_powv_position",
        "thinking_map_outcome",
    }
)
_MAX_CONTEXT_PACKET_BYTES = int(os.environ.get("HESPERIA_MAX_CONTEXT_PACKET_BYTES", "20000"))
_MAX_CONTEXT_PACKET_DEPTH = 6


def _json_depth(value: Any, _current: int = 0) -> int:
    if _current > _MAX_CONTEXT_PACKET_DEPTH:
        return _current
    if isinstance(value, dict):
        return max((_json_depth(v, _current + 1) for v in value.values()), default=_current)
    if isinstance(value, list):
        return max((_json_depth(v, _current + 1) for v in value), default=_current)
    return _current


def _validate_context_packet(cp: dict[str, Any]) -> dict[str, Any]:
    """FPF-HSR-11: reject unknown top-level keys, oversized or overly nested payloads."""
    import json

    unknown = set(cp.keys()) - _CONTEXT_PACKET_ALLOWED_KEYS
    if unknown:
        raise ValueError(f"context_packet: unknown top-level key(s) {sorted(unknown)}")
    size = len(json.dumps(cp))
    if size > _MAX_CONTEXT_PACKET_BYTES:
        raise ValueError(f"context_packet exceeds max size {_MAX_CONTEXT_PACKET_BYTES} bytes")
    depth = _json_depth(cp)
    if depth > _MAX_CONTEXT_PACKET_DEPTH:
        raise ValueError(f"context_packet exceeds max nesting depth {_MAX_CONTEXT_PACKET_DEPTH}")
    return cp


def _rate_limit(key: str = "default") -> bool:
    now = time.monotonic()
    if key not in _RATE:
        _RATE[key] = []
    times = _RATE[key]
    times[:] = [t for t in times if now - t < _RATE_WINDOW]
    if len(times) >= _RATE_LIMIT:
        return False
    times.append(now)
    return True


def _assets_root() -> Path:
    root = os.environ.get("HESPERIA_ASSETS_ROOT")
    if root and Path(root).is_dir():
        d = Path(root) / "assets" / "lexicon" / "curated"
        if d.is_dir():
            return d
    return Path(__file__).resolve().parents[2] / "assets" / "lexicon" / "curated"


def _same_dominant(metrics1: dict, metrics2: dict) -> bool:
    v1 = metrics1.get("macro_domain_vector") or metrics1.get("dominant_macro_domain")
    v2 = metrics2.get("macro_domain_vector") or metrics2.get("dominant_macro_domain")
    if isinstance(v1, list) and isinstance(v2, list):
        i1 = max(range(len(v1)), key=lambda i: v1[i]) if v1 else -1
        i2 = max(range(len(v2)), key=lambda i: v2[i]) if v2 else -1
        return i1 == i2
    return False


def _confidence_delta(d1: dict, d2: dict) -> str:
    c1 = d1.get("TRUST_TIER") or d1.get("OUTPUT_TRUST_TAG") or ""
    c2 = d2.get("TRUST_TIER") or d2.get("OUTPUT_TRUST_TAG") or ""
    return "same" if c1 == c2 else "different"


# Request bodies must be module-level classes: nested models inside create_app() are ForwardRefs
# and break FastAPI/Pydantic v2 body validation (TypeAdapter not fully defined).
from pydantic import BaseModel, Field, field_validator


class AnalyzeBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=_MAX_INPUT_CHARS)
    mode: str = Field(default="standard", pattern="^(reflection|standard)$")
    overlay_hint: dict[str, Any] | None = None
    temp_relation_overlay: list[dict[str, Any]] | None = None


class CompareBody(BaseModel):
    text1: str = Field(..., min_length=1, max_length=_MAX_INPUT_CHARS)
    text2: str = Field(..., min_length=1, max_length=_MAX_INPUT_CHARS)


class BatchAnalyzeBody(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=100)

    @field_validator("texts")
    @classmethod
    def _cap_each(cls, v: list[str]) -> list[str]:
        for i, t in enumerate(v):
            if len(t) > _MAX_INPUT_CHARS:
                raise ValueError(f"texts[{i}] exceeds max length {_MAX_INPUT_CHARS}")
        return v


class InterpretBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=_MAX_INPUT_CHARS)
    mode: str = Field(default="deterministic", pattern="^(deterministic|llm)$")
    overlay_hint: dict[str, Any] | None = None
    temp_relation_overlay: list[dict[str, Any]] | None = None
    # FPF-HSR-11: optional context_packet, allowlisted top-level keys only. Self-contained per
    # request — no server-side session (same statelessness discipline as the rest of this API).
    # Does not flip HESPERIA_GTP_ENABLED; GTP stays feature-gated independent of this field.
    context_packet: dict[str, Any] | None = None
    # FPF-MWI-03 / BUII P7: optional GapReport attach — default off.
    include_gap_report: bool = False
    # CHI-016: Class B TFP-FD opt-in — also requires HESPERIA_TFP_FIELD_DYNAMICS; never default.
    include_tfp_field_dynamics: bool = False

    @field_validator("context_packet")
    @classmethod
    def _validate_context_packet_field(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is None:
            return v
        return _validate_context_packet(v)


def create_app():
    from fastapi import Body, FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse

    from hesperia.system.capabilities import expose_version_endpoint, public_capability

    app = FastAPI(
        title="HESPERIA API",
        description="Product surface: POST /analyze, /compare, /batch, /product/interpret. GET /health.",
        version="1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    if os.environ.get("HESPERIA_REQUIRE_SYSTEM_SEAL", "").strip().lower() in ("1", "true", "yes"):
        repo = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo))
        from hesperia.system.system_seal import run_system_seal_gate

        rep = run_system_seal_gate(repo)
        if rep.get("status") != "PASS":
            raise RuntimeError(
                "HESPERIA system seal FAILED — refusing to serve (set HESPERIA_REQUIRE_SYSTEM_SEAL=0 to disable)."
            )

    def _safe_response(data: dict | list):
        from hesperia.system.version import attach_public_output_metadata, api_pipeline_version, default_calibration_profile
        from runtime.shipping.analyze_profile import attach_analyze_profile, resolve_analyze_profile
        from runtime.shipping.schema_guard import validate_against_public_schema

        cal = default_calibration_profile()
        if resolve_analyze_profile() == "tfp":
            cal = "tfp_v1"
        if isinstance(data, dict):
            merged = attach_public_output_metadata(
                data,
                calibration_profile=cal,
                pipeline_version=api_pipeline_version(),
                execution_flow_version=api_pipeline_version(),
                orchestration_mode="API_SYNC",
            )
        else:
            merged = attach_public_output_metadata(
                {},
                calibration_profile=cal,
                pipeline_version=api_pipeline_version(),
                execution_flow_version=api_pipeline_version(),
                orchestration_mode="API_SYNC",
            )
            merged["payload"] = data
        validate_against_public_schema(merged)
        if isinstance(merged, dict):
            merged = attach_analyze_profile(merged)
        return JSONResponse(content=merged, media_type="application/json")

    def _safe_response_with_engine(data: dict | list, engine_result: dict[str, Any]):
        from hesperia.system.version import attach_public_output_metadata, api_pipeline_version, default_calibration_profile
        from runtime.shipping.analyze_profile import attach_analyze_profile, resolve_analyze_profile
        from runtime.shipping.schema_guard import validate_against_public_schema

        cal = default_calibration_profile()
        if resolve_analyze_profile() == "tfp":
            cal = "tfp_v1"
        if isinstance(data, dict):
            merged = attach_public_output_metadata(
                data,
                calibration_profile=cal,
                pipeline_version=api_pipeline_version(),
                execution_flow_version=api_pipeline_version(),
                orchestration_mode="API_SYNC",
            )
        else:
            merged = attach_public_output_metadata(
                {},
                calibration_profile=cal,
                pipeline_version=api_pipeline_version(),
                execution_flow_version=api_pipeline_version(),
                orchestration_mode="API_SYNC",
            )
            merged["payload"] = data
        validate_against_public_schema(merged)
        merged["engine_result"] = attach_analyze_profile(engine_result)
        if isinstance(merged, dict):
            merged = attach_analyze_profile(merged)
        return JSONResponse(content=merged, media_type="application/json")

    def _neutral_500() -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": "internal_processing_error"},
        )

    @app.exception_handler(ValueError)
    def _handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
        return _neutral_500()

    @app.exception_handler(KeyError)
    def _handle_key_error(request: Request, exc: KeyError) -> JSONResponse:
        return _neutral_500()

    @app.exception_handler(TypeError)
    def _handle_type_error(request: Request, exc: TypeError) -> JSONResponse:
        return _neutral_500()

    @app.exception_handler(Exception)
    def _public_error_boundary(request: Request, exc: Exception) -> JSONResponse:
        from fastapi import HTTPException
        if isinstance(exc, HTTPException):
            raise exc
        return _neutral_500()

    @app.on_event("startup")
    def _startup_fingerprint():
        import sys
        try:
            from runtime.shipping.openai_key_load import ensure_openai_api_key

            ensure_openai_api_key()
        except Exception as exc:
            print(f"openai_key_load skipped: {exc}", file=sys.stderr)
        try:
            from runtime.shipping.analyze_profile import apply_analyze_profile_defaults, resolve_analyze_profile

            prof = apply_analyze_profile_defaults()
            print(f"analyze_profile: {prof}", file=sys.stderr)
        except Exception as exc:
            print(f"analyze_profile init skipped: {exc}", file=sys.stderr)
        try:
            from runtime.shipping.env_guard import check_hesperia_env

            _strict = os.environ.get("HESPERIA_SHIPPING_ENV_STRICT", "").strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
            check_hesperia_env(strict=_strict)
        except Exception:
            pass
        if os.environ.get("HESPERIA_SCHEMA_SHA256"):
            try:
                from runtime.shipping.schema_integrity import verify_public_schema_sha256
                if not verify_public_schema_sha256():
                    print("HESPERIA schema integrity check failed (SHA256 mismatch)", file=sys.stderr)
            except Exception:
                pass
        try:
            from runtime.shipping.version_info import VERSION
            ver = VERSION
        except Exception:
            ver = _runtime_version_fallback()
        print("HESPERIA runtime initialized", file=sys.stderr)
        print(f"version: {ver}", file=sys.stderr)
        print("mode: sealed_evaluator", file=sys.stderr)

    @app.get("/health")
    def health() -> dict[str, Any]:
        from runtime.shipping.analyze_profile import analyze_profile_meta, resolve_analyze_profile

        meta = analyze_profile_meta()
        return {
            "status": "ok",
            "analyze_profile": resolve_analyze_profile(),
            "pack_areas": meta["pack_areas"],
            "pack_families": meta["pack_families"],
            "geometry_areas_lock": meta["geometry_areas_lock"],
            "branch": meta["branch"],
        }

    if expose_version_endpoint():

        @app.get("/version")
        def version() -> dict[str, str]:
            try:
                from runtime.shipping.version_info import VERSION, COMMIT, BUILD

                return {"version": VERSION, "commit": COMMIT, "build": BUILD or "unknown"}
            except Exception:
                return {"version": _runtime_version_fallback(), "commit": "unknown", "build": "unknown"}

    @app.post("/analyze")
    def analyze(analyze_body: AnalyzeBody = Body(...)):
        if not public_capability("analyze"):
            raise HTTPException(status_code=403, detail="Capability disabled")
        if not _rate_limit():
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        from runtime.services.analysis_service import run_structural_analysis
        assets = _assets_root()
        summary_payload = run_structural_analysis(analyze_body.text, assets_root=assets, stages="full")
        from runtime.services.engine_analyze_contract import run_engine_analyze

        engine_result = run_engine_analyze(
            analyze_body.text,
            assets_root=assets,
            overlay_hint=analyze_body.overlay_hint,
            temp_relation_overlay=analyze_body.temp_relation_overlay,
        )
        return _safe_response_with_engine(summary_payload, engine_result)

    @app.post("/compare")
    def compare(compare_body: CompareBody = Body(...)):
        if not public_capability("compare"):
            raise HTTPException(status_code=403, detail="Capability disabled")
        if not _rate_limit():
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        from runtime.services.analysis_service import run_structural_analysis
        assets = _assets_root()
        r1 = run_structural_analysis(compare_body.text1, assets_root=assets, stages="full")
        r2 = run_structural_analysis(compare_body.text2, assets_root=assets, stages="full")
        d1 = (r1.get("L7") or {})
        d2 = (r2.get("L7") or {})
        dom1 = (r1.get("usf") or {}).get("raw_metrics") or {}
        dom2 = (r2.get("usf") or {}).get("raw_metrics") or {}
        out = {
            "run": "compare",
            "text1_preview": compare_body.text1[:80],
            "text2_preview": compare_body.text2[:80],
            "summary1_trust": d1.get("OUTPUT_TRUST_TAG"),
            "summary2_trust": d2.get("OUTPUT_TRUST_TAG"),
            "result1_trust": d1.get("OUTPUT_TRUST_TAG"),
            "result2_trust": d2.get("OUTPUT_TRUST_TAG"),
            "dominant_match": _same_dominant(dom1, dom2),
            "confidence_delta": _confidence_delta(d1, d2),
        }
        return _safe_response(out)

    @app.post("/batch-analyze")
    @app.post("/batch")
    def batch_analyze(batch_body: BatchAnalyzeBody = Body(...)):
        if not public_capability("batch"):
            raise HTTPException(status_code=403, detail="Capability disabled")
        if not _rate_limit():
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        from runtime.services.analysis_service import run_structural_analysis_batch
        assets = _assets_root()
        results = run_structural_analysis_batch(batch_body.texts, assets_root=assets)
        return _safe_response(results)

    @app.post("/product/interpret")
    def product_interpret(interpret_body: InterpretBody = Body(...)):
        if not public_capability("interpret"):
            raise HTTPException(status_code=403, detail="Capability disabled")
        if not _rate_limit():
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        from runtime.services.product_interpret_service import (
            GroundTruthMissingError,
            run_product_interpret,
        )

        assets = _assets_root()
        # FPF-HSR-11: thinking_map_outcome travels inside context_packet on the wire (documented
        # allowlist key) but compile_router_envelope() takes it as its own kwarg — extract here.
        context_packet = dict(interpret_body.context_packet or {})
        thinking_map_outcome = context_packet.pop("thinking_map_outcome", None)
        try:
            result = run_product_interpret(
                interpret_body.text,
                assets_root=assets,
                mode=interpret_body.mode,  # type: ignore[arg-type]
                overlay_hint=interpret_body.overlay_hint,
                temp_relation_overlay=interpret_body.temp_relation_overlay,
                context_packet=context_packet or None,
                thinking_map_outcome=thinking_map_outcome,
                include_gap_report=interpret_body.include_gap_report,
                include_tfp_field_dynamics=interpret_body.include_tfp_field_dynamics,
            )
        except GroundTruthMissingError as exc:
            # FPF-HSR-13: hard fail, not silent omit — never ship a response missing one of the
            # three mandatory engine-governed blocks.
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return JSONResponse(content=result, media_type="application/json")

    return app


# License gate at app load (fail fast before server binds)
if not _license_ok():
    raise RuntimeError("License check failed; cannot start API")

app = create_app()


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HESPERIA_API_HOST", "0.0.0.0")
    port = int(os.environ.get("HESPERIA_API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
