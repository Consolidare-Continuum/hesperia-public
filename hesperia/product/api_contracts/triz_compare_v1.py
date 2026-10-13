# HESPERIA — POST /api/v1/triz/compare contract.

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from hesperia.product.api_contracts.version import API_VERSION


class TrizCompareRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(..., min_length=1, max_length=128)
    project_id: str = Field(..., min_length=1, max_length=128)
    left_corpus_id: str
    right_corpus_id: str
    product_kind: Literal["policy", "innovation", "narrative"]
    report_left: dict[str, Any]
    report_right: dict[str, Any]


class TrizCompareResponseV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: Literal["v1"] = "v1"
    schema_version: str = "triz_compare_v1"
    left_corpus_id: str
    right_corpus_id: str
    product_sku: str
    deltas: dict[str, Any]
    common_signals: list[str]
    emerging_signals: list[str]
    fading_signals: list[str]
    summary_text: str


def validate_triz_compare_response(data: dict[str, Any]) -> TrizCompareResponseV1:
    return TrizCompareResponseV1.model_validate(data)


def wrap_triz_compare_response(comp: Any) -> dict[str, Any]:
    from dataclasses import asdict

    d = asdict(comp) if hasattr(comp, "__dataclass_fields__") else comp
    payload = {
        "api_version": API_VERSION,
        "schema_version": "triz_compare_v1",
        **d,
    }
    return validate_triz_compare_response(payload).model_dump(mode="json")
