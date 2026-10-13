# HESPERIA — hesperia-dev-test API battery. Copyright © 2026 igareosh.com.
"""Structural-invariant battery: synthetic corpus against POST /analyze and POST /product/interpret.

Default mode is in-process (fastapi.testclient.TestClient over runtime.shipping.api_main.create_app),
matching the pattern already used by tests/test_product_interpret_api.py. Live mode (httpx.Client
against a running uvicorn server) is used only for real HTTP-level "API speeds" reporting, not for
the pytest-collected battery.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from tools.hesperia_dev_test.corpus import CorpusEntry, full_corpus

# Volatile keys stripped before determinism comparison — mirrors the
# tests/determinism/test_pipeline_repeatability.py `_diagnostics_structure()` convention.
_VOLATILE_KEYS = frozenset({"execution_time_ms", "duration_ms", "generated_at", "timestamp"})


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_volatile(v) for k, v in value.items() if k not in _VOLATILE_KEYS}
    if isinstance(value, list):
        return [_strip_volatile(v) for v in value]
    return value


@dataclass
class TokenResult:
    entry: CorpusEntry
    analyze_status: int | None = None
    interpret_status: int | None = None
    analyze_ms: float = 0.0
    interpret_ms: float = 0.0
    deterministic: bool | None = None
    error: str | None = None
    analyze_result: dict[str, Any] | None = None
    interpret_result: dict[str, Any] | None = None


def _post(client: Any, path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any], float]:
    t0 = time.perf_counter()
    resp = client.post(path, json=body)
    dt_ms = (time.perf_counter() - t0) * 1000.0
    try:
        payload = resp.json()
    except Exception:
        payload = {}
    return resp.status_code, payload, dt_ms


def run_token(client: Any, entry: CorpusEntry) -> TokenResult:
    result = TokenResult(entry=entry)
    try:
        status1, body1, ms1 = _post(client, "/analyze", {"text": entry.token})
        result.analyze_status = status1
        result.analyze_ms = ms1
        result.analyze_result = body1

        status2, body2, ms2 = _post(
            client, "/product/interpret", {"text": entry.token, "include_gap_report": True}
        )
        result.interpret_status = status2
        result.interpret_ms = ms2
        result.interpret_result = body2

        # Determinism: same token twice through /analyze, compare minus volatile fields.
        _, body1b, _ = _post(client, "/analyze", {"text": entry.token})
        result.deterministic = _strip_volatile(body1) == _strip_volatile(body1b)
    except Exception as exc:  # noqa: BLE001 — the battery records failures, never raises
        result.error = f"{type(exc).__name__}: {exc}"
    return result


def run_battery(client: Any, corpus: list[CorpusEntry] | None = None) -> list[TokenResult]:
    return [run_token(client, entry) for entry in (corpus or full_corpus())]


def in_process_client() -> Any:
    from fastapi.testclient import TestClient

    from runtime.shipping.api_main import create_app

    return TestClient(create_app())


def live_client(base_url: str) -> Any:
    import httpx

    return httpx.Client(base_url=base_url, timeout=30.0)
