# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com — Platonov Igor (aka @igareosh). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# See LEGAL_NOTICE.md for full terms.

"""FPF-V7-11 — LLM integration: Claude/OpenAI over bridge_to_llm_prompt structural state."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol

from sphere.fpf_bridge.bridge import bridge_to_llm_prompt

ProviderName = Literal["openai", "anthropic", "mock"]

SYSTEM_PROMPT = """You are a structural analyst interpreting Hesperia fpf bridge output.
You receive deterministic structural state only — not raw free-form clinical reasoning.
Ground every claim in the supplied structural_state, logic evaluation, and initial_outcome.
Do not invent measurements, scores, or area activations absent from the input."""

STRUCTURAL_NARRATIVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "structural_state",
        "summary",
        "clinical_significance",
        "recommended_actions",
        "confidence",
    ],
    "properties": {
        "structural_state": {"type": "string"},
        "summary": {"type": "string"},
        "clinical_significance": {"type": "string"},
        "recommended_actions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
    },
}


class LlmClient(Protocol):
    def complete_json(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        """Return parsed JSON object matching schema."""


@dataclass(frozen=True)
class LlmInterpretConfig:
    provider: ProviderName = "openai"
    model: str | None = None
    max_output_tokens: int = 2000


def default_openai_model() -> str:
    return os.environ.get(
        "HESPERIA_OPENAI_MODEL",
        os.environ.get("HESPERIA_LLM_INTERPRET_MODEL", "gpt-4o-mini"),
    )


def default_anthropic_model() -> str:
    return os.environ.get("HESPERIA_ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


PAYLOAD_PREFIX = "HESPERIA_BRIDGE_JSON:\n"


def build_interpretation_messages(prompt_state: dict[str, Any]) -> list[dict[str, str]]:
    """Messages for provider APIs — user payload is deterministic bridge JSON only."""
    payload = json.dumps(prompt_state, sort_keys=True, ensure_ascii=False)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Interpret the following Hesperia structural bridge state into a bounded "
                "clinical narrative. Respond with JSON only.\n\n"
                + PAYLOAD_PREFIX
                + payload
            ),
        },
    ]


def _openai_client(cfg: LlmInterpretConfig) -> LlmClient:
    from runtime.shipping.openai_key_load import ensure_openai_api_key

    if not ensure_openai_api_key():
        raise RuntimeError("Missing OPENAI_API_KEY")

    from openai import OpenAI

    model = cfg.model or default_openai_model()
    client = OpenAI()

    class _OpenAIClient:
        def complete_json(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
            resp = client.responses.create(
                model=model,
                temperature=0,
                max_output_tokens=cfg.max_output_tokens,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "structural_narrative",
                        "schema": schema,
                        "strict": True,
                    }
                },
                input=messages,
            )
            try:
                parsed = json.loads(resp.output_text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"OpenAI returned non-JSON output: {resp.output_text[:500]}") from exc
            if not isinstance(parsed, dict):
                raise RuntimeError("OpenAI JSON output must be an object")
            return parsed

    return _OpenAIClient()


def _anthropic_client(cfg: LlmInterpretConfig) -> LlmClient:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("Missing ANTHROPIC_API_KEY")

    import anthropic

    model = cfg.model or default_anthropic_model()
    client = anthropic.Anthropic()

    class _AnthropicClient:
        def complete_json(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
            system = next((m["content"] for m in messages if m["role"] == "system"), SYSTEM_PROMPT)
            user_parts = [m["content"] for m in messages if m["role"] == "user"]
            user_text = "\n\n".join(user_parts)
            resp = client.messages.create(
                model=model,
                max_tokens=cfg.max_output_tokens,
                temperature=0,
                system=system,
                messages=[{"role": "user", "content": user_text}],
            )
            text_blocks = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
            raw = "".join(text_blocks).strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Anthropic returned non-JSON output: {raw[:500]}") from exc
            if not isinstance(parsed, dict):
                raise RuntimeError("Anthropic JSON output must be an object")
            return parsed

    return _AnthropicClient()


def resolve_provider(explicit: ProviderName | None = None) -> ProviderName:
    if explicit and explicit != "mock":
        return explicit
    env = os.environ.get("HESPERIA_LLM_PROVIDER", "").strip().lower()
    if env in ("openai", "anthropic"):
        return env  # type: ignore[return-value]
    if os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        return "anthropic"
    return "openai"


def interpret_prompt_state(
    prompt_state: dict[str, Any],
    *,
    cfg: LlmInterpretConfig | None = None,
    client: LlmClient | None = None,
) -> dict[str, Any]:
    """Call LLM on pre-built bridge prompt state; return audit envelope."""
    config = cfg or LlmInterpretConfig(provider=resolve_provider())
    llm = client if client is not None else _client_for_provider(config)
    messages = build_interpretation_messages(prompt_state)
    narrative = llm.complete_json(messages, STRUCTURAL_NARRATIVE_SCHEMA)
    model = config.model or (
        default_anthropic_model() if config.provider == "anthropic" else default_openai_model()
    )
    return {
        "provider": config.provider,
        "model": model,
        "prompt_state": prompt_state,
        "narrative": narrative,
        "messages": messages,
    }


def interpret_structural_state(
    result: dict[str, Any],
    *,
    cfg: LlmInterpretConfig | None = None,
    client: LlmClient | None = None,
    bridge_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full FPF-V7-11 path: pipeline result → bridge_to_llm_prompt → LLM narrative."""
    bridge_kwargs = bridge_kwargs or {}
    prompt_state = bridge_to_llm_prompt(result, **bridge_kwargs)
    return interpret_prompt_state(prompt_state, cfg=cfg, client=client)


def _client_for_provider(cfg: LlmInterpretConfig) -> LlmClient:
    if cfg.provider == "anthropic":
        return _anthropic_client(cfg)
    if cfg.provider == "openai":
        return _openai_client(cfg)
    raise ValueError(f"Unsupported provider: {cfg.provider}")


def mock_narrative_from_prompt(prompt_state: dict[str, Any]) -> dict[str, Any]:
    """Deterministic mock narrative for tests — no network."""
    state = str(prompt_state.get("current_state") or prompt_state.get("structural_state") or "unknown")
    return {
        "structural_state": state,
        "summary": f"Mock interpretation for structural state {state}.",
        "clinical_significance": "Deterministic test narrative — not clinical advice.",
        "recommended_actions": ["review_structural_evidence", "confirm_with_supervisor"],
        "confidence": "medium",
    }


class MockLlmClient:
    """Test double — derives narrative from prompt_state without API calls."""

    def __init__(self, factory: Callable[[dict[str, Any]], dict[str, Any]] | None = None) -> None:
        self._factory = factory or mock_narrative_from_prompt

    def complete_json(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        del schema
        user = next(m["content"] for m in reversed(messages) if m["role"] == "user")
        if PAYLOAD_PREFIX in user:
            payload = user.split(PAYLOAD_PREFIX, 1)[1].strip()
        else:
            payload = user[user.index("{") :]
        prompt_state = json.loads(payload)
        return self._factory(prompt_state)
