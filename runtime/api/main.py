# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
Hesperia product API — FastAPI.

Product surface: GET /health; POST /hesperia/analyze, /hesperia/compare, /hesperia/batch with Bearer auth
(structural outputs via ``run_structural_analysis`` → projection). **T17:** POST /product/llm-audit,
/product/tfp, /product/fingerprint (``run_product_profile``) — same Bearer; not mounted on shipping ``api_main``.

When ``HESPERIA_PRODUCT_SURFACE`` is true (default), TRIZ and TRIZ MVP routers are not registered.
Set ``HESPERIA_PRODUCT_SURFACE=0`` and ``HESPERIA_EXPOSE_TRIZ=1`` for dev-only TRIZ HTTP exposure.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

_HESPERIA_ROOT = Path(__file__).resolve().parents[2]
_LEXICON_CURATED = _HESPERIA_ROOT / "assets" / "lexicon" / "curated"

from fastapi import Depends, FastAPI, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator

from hesperia.system.version import get_system_version

DEFAULT_TEXT_CAP = int(os.environ.get("HESPERIA_MAX_INPUT_CHARS", "10000"))
API_VERSION = get_system_version()

API_KEY = os.environ.get("HESPERIA_API_KEY", "").strip()
API_KEY_NEXT = os.environ.get("HESPERIA_API_KEY_NEXT", "").strip()
HTTP_BEARER = HTTPBearer(auto_error=False)

_RATE: dict[str, list[float]] = {}
_RATE_LIMIT = int(os.environ.get("HESPERIA_RATE_LIMIT", "60"))
_RATE_WINDOW = 60.0


def _rate_allow(key: str = "default") -> bool:
    now = time.monotonic()
    if key not in _RATE:
        _RATE[key] = []
    times = _RATE[key]
    times[:] = [t for t in times if now - t < _RATE_WINDOW]
    if len(times) >= _RATE_LIMIT:
        return False
    times.append(now)
    return True


def verify_bearer(credentials: HTTPAuthorizationCredentials | None = Security(HTTP_BEARER)) -> None:
    """Bearer auth for product POST routes."""
    if not API_KEY and not API_KEY_NEXT:
        raise PermissionError("Server not configured with HESPERIA_API_KEY")
    if not credentials:
        raise PermissionError("Missing Authorization: Bearer")
    token = credentials.credentials
    if token != API_KEY and token != API_KEY_NEXT:
        raise PermissionError("Invalid API key")


def custom_openapi():
    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["servers"] = [{"url": "https://hesperia.prichindel.com", "description": "Production"}]
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "API Key as Bearer token (GPT Actions: API Key → Bearer)",
    }
    secured_paths = (
        "/hesperia/analyze",
        "/hesperia/compare",
        "/hesperia/batch",
        "/analysis/triz",
        "/product/",
    )
    for path, methods in openapi_schema.get("paths", {}).items():
        if not any(sp in path for sp in secured_paths):
            continue
        for method_name, op in methods.items():
            if method_name != "post":
                continue
            op["security"] = [{"bearerAuth": []}]
            r = op.setdefault("responses", {})
            r.setdefault("429", {"description": "Too Many Requests (rate limit)"})
    app.openapi_schema = openapi_schema
    return app.openapi_schema


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    if API_KEY_NEXT:
        logging.warning("HESPERIA_API_KEY_NEXT is set; rotate then clear it to avoid permanent two-key drift.")
    yield


app = FastAPI(
    title="Hesperia Analyze API",
    version=API_VERSION,
    description="Product surface: analyze / compare / batch (Bearer). Projection enforced; no internal graph exposure.",
    servers=[{"url": "https://hesperia.prichindel.com", "description": "Production"}],
    openapi_url="/openapi.json",
    docs_url=None,
    redoc_url=None,
    lifespan=_lifespan,
)
app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class AnalyzeBody(BaseModel):
    """Single-text analysis (public L1–L9 projection + version envelope)."""

    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., min_length=1, max_length=DEFAULT_TEXT_CAP)


class ProductBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., min_length=1, max_length=DEFAULT_TEXT_CAP)


class CompareBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text1: str = Field(..., min_length=1, max_length=DEFAULT_TEXT_CAP)
    text2: str = Field(..., min_length=1, max_length=DEFAULT_TEXT_CAP)


class BatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texts: list[str] = Field(..., min_length=1, max_length=100)

    @field_validator("texts")
    @classmethod
    def _each_text_cap(cls, v: list[str]) -> list[str]:
        for i, t in enumerate(v):
            if len(t) > DEFAULT_TEXT_CAP:
                raise ValueError(f"texts[{i}] exceeds max length {DEFAULT_TEXT_CAP}")
        return v


class DlcrTraceBody(BaseModel):
    """Dev-only DLCR instrumentation (Ethan PO-26); gated by ``HESPERIA_API_INSTRUMENTATION``."""

    model_config = ConfigDict(extra="forbid")
    text: str = Field(..., min_length=1, max_length=DEFAULT_TEXT_CAP)
    mode: str = Field(default="clinical_speech", max_length=64)


class TrizBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active_graph: dict[str, Any] = Field(...)
    topology: dict[str, Any] | None = Field(default=None)
    narrative_id: str = Field(default="narrative_primary", max_length=256)
    run_id: str | None = Field(default=None, max_length=256)
    topology_mode: bool = Field(default=True)


class ErrorBody(BaseModel):
    error: bool = True
    message: str
    code: int


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


@app.get("/health", response_model=None, summary="Health check")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "hesperia", "version": API_VERSION}


def _assets_curated() -> Path:
    return _LEXICON_CURATED if _LEXICON_CURATED.is_dir() else _HESPERIA_ROOT / "assets" / "lexicon" / "curated"


@app.post("/product/llm-audit", response_model=None)
async def product_llm_audit(body: ProductBody, _: None = Depends(verify_bearer)) -> JSONResponse:
    try:
        from hesperia.product.service import run_product_profile

        payload = run_product_profile(body.text, "llm_audit")
        return JSONResponse(content=payload)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": True, "message": str(e)[:500], "code": 500})


@app.post("/product/tfp", response_model=None)
async def product_tfp(body: ProductBody, _: None = Depends(verify_bearer)) -> JSONResponse:
    try:
        from hesperia.product.service import run_product_profile

        payload = run_product_profile(body.text, "tfp_analysis")
        return JSONResponse(content=payload)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": True, "message": str(e)[:500], "code": 500})


@app.post("/product/fingerprint", response_model=None)
async def product_fingerprint(body: ProductBody, _: None = Depends(verify_bearer)) -> JSONResponse:
    try:
        from hesperia.product.service import run_product_profile

        payload = run_product_profile(body.text, "document_fingerprint")
        return JSONResponse(content=payload)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": True, "message": str(e)[:500], "code": 500})


@app.post("/hesperia/analyze", response_model=None, operation_id="hesperiaAnalyze")
async def hesperia_analyze(
    body: AnalyzeBody,
    _request: Request,
    _: None = Depends(verify_bearer),
) -> JSONResponse:
    from hesperia.system.capabilities import public_capability

    if not public_capability("analyze"):
        return JSONResponse(status_code=403, content={"error": True, "message": "Capability disabled", "code": 403})
    if not _rate_allow():
        return JSONResponse(status_code=429, content={"error": True, "message": "Too many requests", "code": 429})
    try:
        from runtime.services.analysis_service import run_structural_analysis
        from runtime.shipping.schema_guard import validate_against_public_schema

        summary_payload = run_structural_analysis(body.text, assets_root=_assets_curated(), stages="full")
        validate_against_public_schema(summary_payload)
        return JSONResponse(content=summary_payload)
    except ValueError as e:
        msg = str(e)
        if "text_missing" in msg:
            return JSONResponse(status_code=400, content={"error": True, "message": "text missing", "code": 400})
        if "semantic_vacuum" in msg:
            return JSONResponse(
                status_code=400,
                content={"error": True, "message": "No tokens matched any dictionary", "code": 400},
            )
        if "public_schema_violation" in msg:
            return JSONResponse(status_code=500, content={"error": True, "message": "Internal error", "code": 500})
        return JSONResponse(status_code=400, content={"error": True, "message": msg[:500], "code": 400})
    except Exception:
        return JSONResponse(status_code=500, content={"error": True, "message": "Internal error", "code": 500})


@app.post("/hesperia/internal/dlcr_trace", response_model=None, include_in_schema=False)
async def internal_dlcr_trace(
    body: DlcrTraceBody,
    _: None = Depends(verify_bearer),
) -> JSONResponse:
    """
    Returns full ``run_dlcr_pipeline`` JSON (not public-schema-scrubbed).
    Requires ``HESPERIA_API_INSTRUMENTATION=1`` on the server.
    """
    if os.environ.get("HESPERIA_API_INSTRUMENTATION", "").strip().lower() not in ("1", "true", "yes", "on"):
        return JSONResponse(status_code=404, content={"error": True, "message": "instrumentation disabled", "code": 404})
    try:
        from core.engine.lexical_concept.pipeline import run_dlcr_pipeline

        out = run_dlcr_pipeline(body.text, repo_root=_HESPERIA_ROOT, mode=body.mode)
        return JSONResponse(content=out)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": True, "message": str(e)[:500], "code": 500})


@app.post("/hesperia/compare", response_model=None, operation_id="hesperiaCompare")
async def hesperia_compare(
    body: CompareBody,
    _: None = Depends(verify_bearer),
) -> JSONResponse:
    from hesperia.system.capabilities import public_capability
    from hesperia.system.version import attach_public_output_metadata, api_pipeline_version, default_calibration_profile
    from runtime.services.analysis_service import run_structural_analysis
    from runtime.shipping.schema_guard import validate_against_public_schema

    if not public_capability("compare"):
        return JSONResponse(status_code=403, content={"error": True, "message": "Capability disabled", "code": 403})
    if not _rate_allow():
        return JSONResponse(status_code=429, content={"error": True, "message": "Too many requests", "code": 429})
    try:
        assets = _assets_curated()
        r1 = run_structural_analysis(body.text1, assets_root=assets, stages="full")
        r2 = run_structural_analysis(body.text2, assets_root=assets, stages="full")
        d1 = (r1.get("L7") or {}) if isinstance(r1, dict) else {}
        d2 = (r2.get("L7") or {}) if isinstance(r2, dict) else {}
        dom1 = (r1.get("usf") or {}).get("raw_metrics") or {} if isinstance(r1, dict) else {}
        dom2 = (r2.get("usf") or {}).get("raw_metrics") or {} if isinstance(r2, dict) else {}

        def _same_dominant(m1: dict, m2: dict) -> bool:
            v1 = m1.get("macro_domain_vector") or m1.get("dominant_macro_domain")
            v2 = m2.get("macro_domain_vector") or m2.get("dominant_macro_domain")
            if isinstance(v1, list) and isinstance(v2, list):
                i1 = max(range(len(v1)), key=lambda i: v1[i]) if v1 else -1
                i2 = max(range(len(v2)), key=lambda i: v2[i]) if v2 else -1
                return i1 == i2
            return False

        def _conf_delta(x: dict, y: dict) -> str:
            c1 = x.get("TRUST_TIER") or x.get("OUTPUT_TRUST_TAG") or ""
            c2 = y.get("TRUST_TIER") or y.get("OUTPUT_TRUST_TAG") or ""
            return "same" if c1 == c2 else "different"

        comparison = {
            "run": "compare",
            "text1_preview": body.text1[:80],
            "text2_preview": body.text2[:80],
            "summary1_trust": d1.get("OUTPUT_TRUST_TAG"),
            "summary2_trust": d2.get("OUTPUT_TRUST_TAG"),
            "result1_trust": d1.get("OUTPUT_TRUST_TAG"),
            "result2_trust": d2.get("OUTPUT_TRUST_TAG"),
            "dominant_match": _same_dominant(dom1, dom2),
            "confidence_delta": _conf_delta(d1, d2),
        }
        wrapped = attach_public_output_metadata(
            comparison,
            calibration_profile=default_calibration_profile(),
            pipeline_version=api_pipeline_version(),
            execution_flow_version=api_pipeline_version(),
            orchestration_mode="API_SYNC",
        )
        validate_against_public_schema(wrapped)
        return JSONResponse(content=wrapped)
    except Exception:
        return JSONResponse(status_code=500, content={"error": True, "message": "Internal error", "code": 500})


@app.post("/hesperia/batch", response_model=None, operation_id="hesperiaBatch")
async def hesperia_batch(
    body: BatchBody,
    _: None = Depends(verify_bearer),
) -> JSONResponse:
    from hesperia.system.capabilities import public_capability
    from hesperia.system.version import attach_public_output_metadata, api_pipeline_version, default_calibration_profile
    from runtime.services.analysis_service import run_structural_analysis_batch
    from runtime.shipping.schema_guard import validate_against_public_schema

    if not public_capability("batch"):
        return JSONResponse(status_code=403, content={"error": True, "message": "Capability disabled", "code": 403})
    if not _rate_allow():
        return JSONResponse(status_code=429, content={"error": True, "message": "Too many requests", "code": 429})
    try:
        assets = _assets_curated()
        results = run_structural_analysis_batch(body.texts, assets_root=assets)
        wrapped = attach_public_output_metadata(
            {},
            calibration_profile=default_calibration_profile(),
            pipeline_version=api_pipeline_version(),
            execution_flow_version=api_pipeline_version(),
            orchestration_mode="API_SYNC",
        )
        wrapped["payload"] = results
        validate_against_public_schema(wrapped)
        return JSONResponse(content=wrapped)
    except Exception:
        return JSONResponse(status_code=500, content={"error": True, "message": "Internal error", "code": 500})


from hesperia.system.capabilities import expose_triz_api

if expose_triz_api():

    @app.post("/analysis/triz", response_model=None, summary="TRIZ (dev only when exposed)")
    async def analysis_triz(
        body: TrizBody,
        _: None = Depends(verify_bearer),
    ) -> JSONResponse:
        try:
            from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
            from hesperia.system.version import attach_public_output_metadata, default_calibration_profile, triz_pipeline_version

            ag = active_graph_from_payload(body.active_graph)
            content = run_triz_analysis_complete(
                ag,
                body.topology,
                narrative_id=body.narrative_id,
                run_id=body.run_id,
                topology_mode=body.topology_mode,
            )
            wrapped = attach_public_output_metadata(
                content if isinstance(content, dict) else {"triz_payload": content},
                calibration_profile=default_calibration_profile(),
                pipeline_version=triz_pipeline_version(),
                execution_flow_version=triz_pipeline_version(),
                orchestration_mode="API_SYNC",
            )
            return JSONResponse(content=wrapped)
        except Exception:
            return JSONResponse(status_code=500, content={"error": True, "message": "Internal error", "code": 500})

    try:
        from runtime.api.triz_mvp_v1 import router as triz_mvp_router

        app.include_router(triz_mvp_router)
    except Exception:
        pass


# --- TFP-CHROMA-04: Inspector/API composition (spec §6) ---
_CHROMA_HOST = os.environ.get("HESPERIA_CHROMA_HOST", "localhost")
_CHROMA_PORT = int(os.environ.get("HESPERIA_CHROMA_PORT", "8002"))
_CHROMA_COLLECTION = os.environ.get("HESPERIA_CHROMA_COLLECTION", "knowledge")
_TFP_CORPUS_LAYER = "tfp_corpus_ru"


class TfpCorpusComposeBody(BaseModel):
    """Compose a Chroma query from iteration context and retrieve tfp_corpus_ru chunks (spec §6)."""

    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(..., min_length=1, max_length=256)
    iteration_labels: list[str] = Field(default_factory=list, max_length=50)
    relational_summary: str = Field(default="", max_length=2000)
    query: str = Field(default="", max_length=1000)
    n_results: int = Field(default=5, ge=1, le=20)


@app.post("/inspector/tfp-corpus/compose", response_model=None, summary="TFP corpus composition (spec §6)")
async def inspector_tfp_corpus_compose(
    body: TfpCorpusComposeBody,
    _: None = Depends(verify_bearer),
) -> JSONResponse:
    parts: list[str] = []
    if body.iteration_labels:
        parts.append("Iteration context: " + ", ".join(body.iteration_labels[:20]))
    if body.relational_summary:
        parts.append(body.relational_summary[:1500])
    if body.query:
        parts.append(body.query)
    composed_query = " ".join(parts).strip() or body.session_id
    try:
        import chromadb

        client = chromadb.HttpClient(host=_CHROMA_HOST, port=_CHROMA_PORT)
        col = client.get_collection(_CHROMA_COLLECTION)
        res = col.query(
            query_texts=[composed_query],
            n_results=body.n_results,
            where={"layer": _TFP_CORPUS_LAYER},
            include=["documents", "metadatas", "distances"],
        )
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0]
        chunks = [
            {"rank": i + 1, "document": d, "source": m.get("source", ""), "distance": round(float(dist), 4)}
            for i, (d, m, dist) in enumerate(zip(docs, metas, distances))
        ]
        return JSONResponse(content={
            "session_id": body.session_id,
            "corpus_layer": _TFP_CORPUS_LAYER,
            "query": composed_query[:500],
            "n_results": len(chunks),
            "chunks": chunks,
            "corpus_available": bool(chunks),
        })
    except Exception as e:
        err = str(e)
        corpus_absent = "does not exist" in err or "not found" in err.lower() or "no results" in err.lower()
        return JSONResponse(
            status_code=503 if corpus_absent else 500,
            content={
                "error": True,
                "session_id": body.session_id,
                "corpus_layer": _TFP_CORPUS_LAYER,
                "corpus_available": False,
                "message": "tfp_corpus_ru not ingested" if corpus_absent else f"Chroma error: {err[:300]}",
                "code": 503 if corpus_absent else 500,
            },
        )


@app.exception_handler(PermissionError)
async def permission_handler(_request: Request, exc: PermissionError) -> JSONResponse:
    msg = str(exc)
    if "not configured" in msg:
        return JSONResponse(status_code=503, content={"error": True, "message": "Service not configured", "code": 503})
    return JSONResponse(
        status_code=401,
        content={"error": True, "message": "Missing or invalid Authorization", "code": 401},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    msg = "Invalid request body"
    for e in exc.errors() or []:
        if e.get("type") == "extra_forbidden" or "extra" in (e.get("msg") or "").lower():
            msg = "Invalid request body: extra fields not permitted"
            break
    return JSONResponse(
        status_code=422,
        content={"error": True, "message": msg, "code": 422},
    )
