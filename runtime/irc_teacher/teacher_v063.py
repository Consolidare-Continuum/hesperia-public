"""Hesperia 0.6.3 — OpenAI Teacher client (values-only JSON, H063-20..25)."""
from __future__ import annotations

import json
import os
from typing import Any, Mapping

FORBIDDEN_KEYS = frozenset({"justification", "message", "explanation", "reasoning", "comment"})

RU_SYSTEM_PROMPT = (
    "Ты инспектор параметров графа Hesperia. "
    "Верни только JSON по схеме hesperia.teacher_response.v063. "
    "Поле proposals: только action и числовые значения. "
    "Без текста, без объяснений, без justification."
)


def validate_teacher_response_v063(data: Mapping[str, Any]) -> None:
    if data.get("schema") != "hesperia.teacher_response.v063":
        raise ValueError("invalid schema")
    if data.get("lang") != "ru":
        raise ValueError("lang must be ru")
    proposals = data.get("proposals")
    if not isinstance(proposals, list):
        raise ValueError("proposals must be array")
    for p in proposals:
        if not isinstance(p, dict):
            raise ValueError("proposal must be object")
        extra = set(p.keys()) & FORBIDDEN_KEYS
        if extra:
            raise ValueError(f"forbidden keys: {extra}")
        for k, v in p.items():
            if isinstance(v, str) and k not in ("action", "source", "target", "type", "concept_id", "field"):
                raise ValueError(f"unexpected string field {k}")


def compute_reweight_preview(proposals: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for p in proposals:
        action = p.get("action")
        if action == "update_edge_weight":
            preview.append(
                {
                    "parameter_key": f"W_e:{p.get('source')}->{p.get('target')}",
                    "value_before": p.get("W_e_current"),
                    "value_after": p.get("W_e_proposed"),
                    "applied": 0,
                }
            )
        elif action == "update_cd_field":
            preview.append(
                {
                    "parameter_key": f"{p.get('concept_id')}.{p.get('field')}",
                    "value_before": p.get("value_current"),
                    "value_after": p.get("value_proposed"),
                    "applied": 0,
                }
            )
    return preview


def call_openai_teacher_v063(
    teacher_request: Mapping[str, Any],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or os.environ.get("HESPERIA_KSI_LLM_TEACHER", "0").strip() != "1":
        return {"schema": "hesperia.teacher_response.v063", "lang": "ru", "proposals": []}

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package required") from exc

    client = OpenAI(api_key=api_key)
    model_name = model or os.environ.get("HESPERIA_KSI_TEACHER_MODEL", "gpt-4o-mini")
    user_payload = json.dumps(teacher_request, ensure_ascii=False)
    resp = client.chat.completions.create(
        model=model_name,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": RU_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
        temperature=0,
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    if "schema" not in data:
        data = {"schema": "hesperia.teacher_response.v063", "lang": "ru", **data}
    validate_teacher_response_v063(data)
    return data
