# HESPERIA — POST /api/v1/triz/export contract.

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from hesperia.product.api_contracts.version import API_VERSION


class TrizExportRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(..., min_length=1, max_length=128)
    project_id: str = Field(..., min_length=1, max_length=128)
    corpus_id: str
    product_mode: Literal["policy_detector", "innovation_radar", "narrative_monitor"]
    triz_full: dict[str, Any]


class TrizExportResponseV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: Literal["v1"] = "v1"
    schema_version: str = "triz_export_v1"
    sku: str
    bundle: dict[str, Any]


def validate_triz_export_response(data: dict[str, Any]) -> TrizExportResponseV1:
    if not data.get("sku"):
        raise ValueError("export contract: sku required")
    b = data.get("bundle") or {}
    if "report" not in b:
        raise ValueError("export contract: bundle.report required")
    return TrizExportResponseV1.model_validate(data)


def wrap_triz_export_response(sku: str, bundle: dict[str, Any]) -> dict[str, Any]:
    payload = {"api_version": API_VERSION, "schema_version": "triz_export_v1", "sku": sku, "bundle": bundle}
    if "report" not in bundle:
        raise ValueError("bundle.report required")
    return validate_triz_export_response(payload).model_dump(mode="json")
