# HESPERIA — Reference Architecture Definition (RAD)
# Frozen TRIZ MVP API v1 routes.

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials

from runtime.api.main import HTTP_BEARER, verify_bearer

router = APIRouter(prefix="/api/v1/triz", tags=["triz-mvp-v1"])

TRIZ_ENABLE_COMPARE = os.environ.get("TRIZ_ENABLE_COMPARE", "true").lower() in ("1", "true", "yes")
TRIZ_ENABLE_EXPORT = os.environ.get("TRIZ_ENABLE_EXPORT", "true").lower() in ("1", "true", "yes")


def _auth():
    return Depends(verify_bearer)


@router.post("/analyze")
async def triz_analyze_v1(
    body: dict[str, Any],
    credentials: HTTPAuthorizationCredentials | None = Security(HTTP_BEARER),
) -> JSONResponse:
    verify_bearer(credentials)
    from hesperia.extensions.triz.pipeline import active_graph_from_payload, run_triz_analysis_complete
    from hesperia.product.api_contracts.triz_analysis_v1 import TrizAnalyzeRequestV1, wrap_triz_analyze_response

    req = TrizAnalyzeRequestV1.model_validate(body)
    ag = active_graph_from_payload(req.active_graph)
    triz = run_triz_analysis_complete(
        ag,
        req.topology,
        narrative_id=req.narrative_id,
        topology_mode=req.topology_mode,
    )
    try:
        out = wrap_triz_analyze_response(req.corpus_id, triz)
    except ValueError as e:
        return JSONResponse(status_code=500, content={"error": True, "message": str(e), "code": 500})
    return JSONResponse(content=out)


@router.post("/compare")
async def triz_compare_v1(
    body: dict[str, Any],
    credentials: HTTPAuthorizationCredentials | None = Security(HTTP_BEARER),
) -> JSONResponse:
    verify_bearer(credentials)
    if not TRIZ_ENABLE_COMPARE:
        return JSONResponse(status_code=403, content={"error": True, "message": "compare disabled", "code": 403})
    from hesperia.product.api_contracts.triz_compare_v1 import TrizCompareRequestV1, wrap_triz_compare_response
    from hesperia.product.comparison_engine import compare_reports_unified
    from hesperia.product.package_builder import PRODUCT_SKUS

    req = TrizCompareRequestV1.model_validate(body)
    kind = req.product_kind
    sku = {
        "policy": PRODUCT_SKUS["policy_detector"],
        "innovation": PRODUCT_SKUS["innovation_radar"],
        "narrative": PRODUCT_SKUS["narrative_monitor"],
    }[kind]
    comp = compare_reports_unified(
        req.left_corpus_id,
        req.right_corpus_id,
        sku,
        req.report_left,
        req.report_right,
        product_kind=kind,
    )
    try:
        out = wrap_triz_compare_response(comp)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": True, "message": str(e), "code": 500})
    return JSONResponse(content=out)


@router.post("/export")
async def triz_export_v1(
    body: dict[str, Any],
    credentials: HTTPAuthorizationCredentials | None = Security(HTTP_BEARER),
) -> JSONResponse:
    verify_bearer(credentials)
    if not TRIZ_ENABLE_EXPORT:
        return JSONResponse(status_code=403, content={"error": True, "message": "export disabled", "code": 403})
    from hesperia.product.api_contracts.triz_export_v1 import TrizExportRequestV1, wrap_triz_export_response
    from hesperia.product.package_builder import build_innovation_package, build_narrative_package, build_policy_package

    req = TrizExportRequestV1.model_validate(body)
    if req.product_mode == "policy_detector":
        pkg = build_policy_package(req.triz_full, req.corpus_id)
    elif req.product_mode == "innovation_radar":
        pkg = build_innovation_package(req.triz_full, req.corpus_id)
    else:
        pkg = build_narrative_package(req.triz_full, req.corpus_id)
    inner = {k: v for k, v in pkg.items() if k != "sku"}
    try:
        out = wrap_triz_export_response(pkg["sku"], inner)
    except ValueError as e:
        return JSONResponse(status_code=500, content={"error": True, "message": str(e), "code": 500})
    return JSONResponse(content=out)


@router.post("/signals/core")
async def triz_signals_core(
    body: dict[str, Any],
    credentials: HTTPAuthorizationCredentials | None = Security(HTTP_BEARER),
) -> JSONResponse:
    """Core commercial signals (policy tension, coherence drivers, innovation, narrative, system)."""
    verify_bearer(credentials)
    from hesperia.extensions.triz.commercial_intelligence import extract_core_commercial_signals

    triz = body.get("triz") if isinstance(body.get("triz"), dict) else body
    if not isinstance(triz, dict):
        return JSONResponse(status_code=400, content={"error": True, "message": "triz object required", "code": 400})
    return JSONResponse(content={"core_signals": extract_core_commercial_signals(triz)})


@router.post("/signals/contradiction-index")
async def triz_contradiction_index(
    body: dict[str, Any],
    credentials: HTTPAuthorizationCredentials | None = Security(HTTP_BEARER),
) -> JSONResponse:
    verify_bearer(credentials)
    triz = body.get("triz") if isinstance(body.get("triz"), dict) else body
    if not isinstance(triz, dict):
        return JSONResponse(status_code=400, content={"error": True, "message": "triz object required", "code": 400})
    ci = triz.get("commercial_intelligence") or {}
    cs = ci.get("core_signals") or {}
    am = triz.get("atomic_metrics") or {}
    return JSONResponse(
        content={
            "contradiction_index": {
                "policy_tension_index": cs.get("policy_tension_index", 0.0),
                "contradiction_density": am.get("contradiction_density", 0.0),
                "cross_area_contradiction_rate": cs.get("cross_area_contradiction_rate", 0.0),
                "contradiction_count": am.get("contradiction_count", 0),
            }
        }
    )


@router.post("/signals/innovation-clusters")
async def triz_innovation_clusters_signal(
    body: dict[str, Any],
    credentials: HTTPAuthorizationCredentials | None = Security(HTTP_BEARER),
) -> JSONResponse:
    verify_bearer(credentials)
    triz = body.get("triz") if isinstance(body.get("triz"), dict) else body
    if not isinstance(triz, dict):
        return JSONResponse(status_code=400, content={"error": True, "message": "triz object required", "code": 400})
    inn = (triz.get("commercial_intelligence") or {}).get("innovation_intelligence_products") or {}
    return JSONResponse(content={"innovation_clusters": inn.get("innovation_radar", {}), "raw_clusters": triz.get("innovation_clusters", [])})


@router.post("/signals/narrative-penetration")
async def triz_narrative_penetration_signal(
    body: dict[str, Any],
    credentials: HTTPAuthorizationCredentials | None = Security(HTTP_BEARER),
) -> JSONResponse:
    verify_bearer(credentials)
    triz = body.get("triz") if isinstance(body.get("triz"), dict) else body
    if not isinstance(triz, dict):
        return JSONResponse(status_code=400, content={"error": True, "message": "triz object required", "code": 400})
    nar = (triz.get("commercial_intelligence") or {}).get("narrative_intelligence_products") or {}
    return JSONResponse(content={"narrative_penetration": nar})
