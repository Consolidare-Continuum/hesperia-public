# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

"""Optional LLM narrative over RouterPromptEnvelope (FPF-V7-11/12, HSR-V7-D-21..25)."""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol

from sphere.router.llm_call_log import LlmCallTimer, log_llm_call
from sphere.router.prompt_envelope import (
    PromptPolicyViolation,
    build_prompt_envelope,
    enforce_prompt_policy_or_raise,
)

ProviderName = Literal["openai", "anthropic", "mock"]

SYSTEM_PROMPT = """You are a structural analyst interpreting a Hesperia v7 router prompt envelope.
Ground every claim in engine_trace, logic_mapping, retrieval_context, and policy_block only.
Do not invent measurements absent from the input. Do not treat hidden reasoning as evidence."""

PAYLOAD_PREFIX = "HESPERIA_ROUTER_PROMPT_JSON:\n"

STRUCTURAL_NARRATIVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "clinical_significance", "recommended_actions", "confidence"],
    "properties": {
        "summary": {"type": "string"},
        "clinical_significance": {"type": "string"},
        "recommended_actions": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
}

_EMPTY_NARRATIVE: dict[str, Any] = {
    "summary": "",
    "clinical_significance": "",
    "recommended_actions": [],
    "confidence": "low",
}


def default_openai_model() -> str:
    return os.environ.get(
        "HESPERIA_OPENAI_MODEL",
        os.environ.get("HESPERIA_LLM_INTERPRET_MODEL", "gpt-4o-mini"),
    )


def default_anthropic_model() -> str:
    return os.environ.get("HESPERIA_ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


def _resolved_model(config: LlmInterpretConfig) -> str:
    if config.model:
        return config.model
    if config.provider == "anthropic":
        return default_anthropic_model()
    if config.provider == "openai":
        return default_openai_model()
    return "mock"


class LlmClient(Protocol):
    def complete_json(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class LlmInterpretConfig:
    provider: ProviderName = "openai"
    model: str | None = None
    max_output_tokens: int = 2000
    timeout_seconds: float = 30.0
    max_retries: int = 1


class LlmCallTimeout(Exception):
    """Raised when provider call exceeds configured timeout."""


def _config_from_env(cfg: LlmInterpretConfig | None) -> LlmInterpretConfig:
    base = cfg or LlmInterpretConfig(provider="mock")
    timeout_raw = os.environ.get("HESPERIA_LLM_TIMEOUT_SEC", "").strip()
    retry_raw = os.environ.get("HESPERIA_LLM_MAX_RETRIES", "").strip()
    timeout = float(timeout_raw) if timeout_raw else base.timeout_seconds
    retries = int(retry_raw) if retry_raw else base.max_retries
    provider = base.provider
    env_provider = os.environ.get("HESPERIA_LLM_PROVIDER", "").strip().lower()
    if (not cfg or cfg.provider == "mock") and env_provider in ("openai", "anthropic", "mock"):
        provider = env_provider  # type: ignore[assignment]
    model = base.model or (os.environ.get("HESPERIA_LLM_INTERPRET_MODEL") or "").strip() or None
    return LlmInterpretConfig(
        provider=provider,  # type: ignore[arg-type]
        model=model,
        max_output_tokens=base.max_output_tokens,
        timeout_seconds=max(0.1, timeout),
        max_retries=max(0, retries),
    )


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


def _client_for_provider(cfg: LlmInterpretConfig) -> LlmClient:
    if cfg.provider == "mock":
        return MockLlmClient()
    if cfg.provider == "anthropic":
        return _anthropic_client(cfg)
    if cfg.provider == "openai":
        return _openai_client(cfg)
    raise ValueError(f"Unsupported provider: {cfg.provider}")


def _output_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_interpretation_messages(prompt_envelope: dict[str, Any]) -> list[dict[str, str]]:
    payload = json.dumps(prompt_envelope, sort_keys=True, ensure_ascii=False)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Interpret this router prompt envelope into a bounded structural narrative. "
                "Respond with JSON only.\n\n" + PAYLOAD_PREFIX + payload
            ),
        },
    ]


def mock_narrative_from_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    trace = envelope.get("engine_trace") or {}
    dom = trace.get("dominant_area_id", "unknown")
    return {
        "summary": f"Mock interpretation — dominant area {dom}.",
        "clinical_significance": "Deterministic test narrative — not clinical advice.",
        "recommended_actions": ["review_engine_trace", "confirm_with_supervisor"],
        "confidence": "medium",
    }


class MockLlmClient:
    def __init__(
        self,
        factory: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        *,
        delay_seconds: float = 0.0,
        fail_times: int = 0,
    ) -> None:
        self._factory = factory or mock_narrative_from_envelope
        self._delay_seconds = delay_seconds
        self._fail_times = fail_times
        self._calls = 0

    def complete_json(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        del schema
        self._calls += 1
        if self._fail_times >= self._calls:
            raise RuntimeError("mock provider failure")
        if self._delay_seconds > 0:
            import time

            time.sleep(self._delay_seconds)
        user = next(m["content"] for m in reversed(messages) if m["role"] == "user")
        marker = PAYLOAD_PREFIX
        payload = user.split(marker, 1)[1].strip() if marker in user else user[user.index("{") :]
        return self._factory(json.loads(payload))


def _call_with_timeout(
    client: LlmClient,
    messages: list[dict[str, str]],
    schema: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(client.complete_json, messages, schema)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            raise LlmCallTimeout(f"LLM call exceeded {timeout_seconds}s") from exc


def _invoke_with_retry(
    client: LlmClient,
    messages: list[dict[str, str]],
    schema: dict[str, Any],
    config: LlmInterpretConfig,
) -> tuple[dict[str, Any], int]:
    last_error: Exception | None = None
    attempts = config.max_retries + 1
    for attempt in range(1, attempts + 1):
        try:
            narrative = _call_with_timeout(
                client,
                messages,
                schema,
                config.timeout_seconds,
            )
            return narrative, attempt
        except (LlmCallTimeout, OSError, RuntimeError, Exception) as exc:
            # Provider SDKs raise typed HTTP errors (e.g. openai.AuthenticationError)
            # that are not RuntimeError subclasses — still retry/fail cleanly.
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            last_error = exc
            if attempt >= attempts:
                break
    assert last_error is not None
    raise last_error


def interpret_router_envelope(
    envelope: dict[str, Any],
    *,
    cfg: LlmInterpretConfig | None = None,
    client: LlmClient | None = None,
) -> dict[str, Any]:
    """LLM call wrapper: prompt envelope → narrative + hashes + call metadata."""
    config = _config_from_env(cfg)
    llm = client if client is not None else _client_for_provider(config)
    model_name = _resolved_model(config)
    input_hash = str(envelope.get("input_hash") or "")
    prompt_env = build_prompt_envelope(envelope)
    try:
        enforce_prompt_policy_or_raise(prompt_env)
    except PromptPolicyViolation as exc:
        result = {
            "provider": config.provider,
            "model": model_name,
            "prompt_envelope": prompt_env,
            "narrative": dict(_EMPTY_NARRATIVE),
            "output_hash": _output_hash(_EMPTY_NARRATIVE),
            "call_status": "policy_violation",
            "policy_violations": exc.violations,
        }
        log_llm_call(
            input_hash=input_hash,
            output_hash=result["output_hash"],
            provider=config.provider,
            model=model_name,
            latency_ms=0.0,
            status="policy_violation",
            error=";".join(exc.violations),
        )
        return result

    messages = build_interpretation_messages(prompt_env)
    timer = LlmCallTimer()
    try:
        narrative, attempt = _invoke_with_retry(
            llm,
            messages,
            STRUCTURAL_NARRATIVE_SCHEMA,
            config,
        )
        latency = timer.elapsed_ms()
        out_hash = _output_hash(narrative)
        log_llm_call(
            input_hash=input_hash,
            output_hash=out_hash,
            provider=config.provider,
            model=model_name,
            latency_ms=latency,
            status="ok",
            attempt=attempt,
        )
        return {
            "provider": config.provider,
            "model": model_name,
            "prompt_envelope": prompt_env,
            "narrative": narrative,
            "output_hash": out_hash,
            "call_status": "ok",
            "latency_ms": round(latency, 3),
            "attempt": attempt,
        }
    except (LlmCallTimeout, OSError, RuntimeError, Exception) as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        latency = timer.elapsed_ms()
        out_hash = _output_hash(_EMPTY_NARRATIVE)
        err = str(exc)
        # Never echo raw API keys from provider error payloads into responses.
        if "sk-" in err:
            err = "provider_auth_or_request_failed"
        log_llm_call(
            input_hash=input_hash,
            output_hash=out_hash,
            provider=config.provider,
            model=model_name,
            latency_ms=latency,
            status="failed",
            error=err,
            attempt=config.max_retries + 1,
        )
        return {
            "provider": config.provider,
            "model": model_name,
            "prompt_envelope": prompt_env,
            "narrative": dict(_EMPTY_NARRATIVE),
            "output_hash": out_hash,
            "call_status": "failed",
            "call_error": err,
            "latency_ms": round(latency, 3),
        }
