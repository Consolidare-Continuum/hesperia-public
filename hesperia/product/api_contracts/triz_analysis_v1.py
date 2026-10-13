# HESPERIA — POST /api/v1/triz/analyze contract.

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from hesperia.product.api_contracts.version import API_VERSION


class TrizAnalyzeRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(..., min_length=1, max_length=128)
    project_id: str = Field(..., min_length=1, max_length=128)
    corpus_id: str = Field(..., min_length=1, max_length=256)
    active_graph: dict[str, Any]
    topology: dict[str, Any] | None = None
    narrative_id: str = Field(default="narrative_primary", max_length=256)
    topology_mode: bool = True


class TrizAnalyzeResponseV1(BaseModel):
    """Frozen response envelope; inner triz payload validated for required keys."""

    model_config = ConfigDict(extra="forbid")
    api_version: Literal["v1"] = "v1"
    schema_version: str = Field(default="triz_api_v1")
    corpus_id: str
    triz: dict[str, Any]


def validate_triz_analyze_response(data: dict[str, Any]) -> TrizAnalyzeResponseV1:
    t = data.get("triz") or {}
    for req in ("contradictions", "innovation_clusters", "narratives"):
        if req not in t:
            raise ValueError(f"TRIZ response contract violation: missing '{req}'")
    return TrizAnalyzeResponseV1.model_validate(data)


def wrap_triz_analyze_response(corpus_id: str, triz: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "api_version": API_VERSION,
        "schema_version": "triz_api_v1",
        "corpus_id": corpus_id,
        "triz": triz,
    }
    return validate_triz_analyze_response(payload).model_dump(mode="json")
