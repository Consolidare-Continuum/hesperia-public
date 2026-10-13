"""Build OpenAI Chat-style messages[] + finalize export segment."""

from __future__ import annotations

import copy
from typing import Any

from .constants import PROMPT_PACK_ID_KERNBERG_V1, SEGMENT_SCHEMA_VERSION
from .prompt_pack import load_system_prompt_kernberg_v1, render_user_prompt_kernberg_v1


def _primary_client_text(sentences: list[dict[str, Any]]) -> str:
    if not sentences:
        return ""
    parts = sorted(sentences, key=lambda s: int(s.get("order", 0)))
    return "\n".join(str(s.get("text", "")) for s in parts)


def _parameters_summary(parameters: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in sorted(parameters.keys())[:80]:
        val = parameters[key]
        if isinstance(val, (dict, list)):
            lines.append(f"- {key}: <structured>")
        else:
            s = str(val)
            if len(s) > 120:
                s = s[:117] + "..."
            lines.append(f"- {key}: {s}")
    return "\n".join(lines) if lines else "(no parameters)"


def build_openai_messages(segment: dict[str, Any]) -> list[dict[str, str]]:
    """T08–T10: system + user messages for Chat Completions. T63: len >= 2, roles system+user."""
    seg = copy.deepcopy(segment)
    # Strip messages if re-calling
    seg.pop("messages", None)
    client_text = _primary_client_text(seg.get("sentences") or [])
    summary = _parameters_summary(seg.get("parameters") or {})
    user_content = render_user_prompt_kernberg_v1(
        segment_json_for_llm=seg,
        client_text_plain=client_text,
        parameters_summary_lines=summary,
    )
    system_content = load_system_prompt_kernberg_v1()
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def finalize_segment_openai_v1(
    segment_without_messages: dict[str, Any],
    *,
    prompt_pack_id: str = PROMPT_PACK_ID_KERNBERG_V1,
) -> dict[str, Any]:
    """Attach schema_version, prompt_pack_id, schema-valid messages."""
    out = copy.deepcopy(segment_without_messages)
    out["schema_version"] = SEGMENT_SCHEMA_VERSION
    out["prompt_pack_id"] = prompt_pack_id
    out["messages"] = build_openai_messages(out)
    return out
