"""Engine /analyze adapter for IRC Teacher path (product repo; HTTP to Hesperia engine)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from runtime.irc_teacher.flags import engine_enabled, engine_url


@dataclass
class HybridRetrieveInput:
    query: str
    mode: str = "hybrid"


@dataclass
class HybridRetrieveOutput:
    engine_result: dict[str, Any] | None = None
    interior_pov: dict[str, Any] | None = None
    gtp_coherence: dict[str, Any] | None = None
    context_package: dict[str, Any] | None = None
    cobalt_retrieval: dict[str, Any] | None = None


def _extract_engine_analyze_result(payload: dict[str, Any]) -> dict[str, Any]:
    sidecar = payload.get("engine_result")
    if isinstance(sidecar, dict) and sidecar.get("trace") is not None:
        return sidecar
    return payload


def _call_engine(query: str, timeout_s: float = 8.0) -> dict[str, Any] | None:
    if not engine_enabled():
        return None
    base = engine_url().rstrip("/")
    url = f"{base}/analyze"
    body = json.dumps({"text": query, "mode": "standard"}).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
            data = json.loads(payload)
            return _extract_engine_analyze_result(data)
    except (URLError, OSError, json.JSONDecodeError, ValueError):
        return None


def retrieve(inp: HybridRetrieveInput) -> HybridRetrieveOutput:
    """Minimal hybrid retrieve: engine /analyze + KSI block + optional COBALT.

    Wire: if engine envelope lacks ``ksi`` and ``HESPERIA_KSI_ENABLED=1``, run
    ``core.domain.ksi.pipeline.attach_ksi_to_engine_result`` locally (same entry as sealed analyze).
    """
    engine_result = _call_engine(inp.query.strip())
    ksi_block: dict[str, Any] = {}
    interior_pov = None
    gtp_coherence = None
    if isinstance(engine_result, dict):
        try:
            from core.domain.ksi.pipeline import attach_ksi_to_engine_result

            engine_result = attach_ksi_to_engine_result(engine_result)
        except Exception:
            pass
        ksi_block = engine_result.get("ksi") or {}
        interior_pov = engine_result.get("interior_pov")
        gtp_coherence = engine_result.get("gtp_coherence")
    context_package = {"ksi": ksi_block} if ksi_block else {}
    cobalt_packet = None
    try:
        from runtime.cobalt.flags import cobalt_enabled
        from runtime.cobalt.retrieve import compose_and_retrieve

        if cobalt_enabled():
            cobalt_packet = compose_and_retrieve(
                inp.query.strip(),
                engine_result=engine_result,
                strategy="S1",
            )
            context_package = {**context_package, "cobalt_retrieval": cobalt_packet}
    except Exception:
        cobalt_packet = None
    return HybridRetrieveOutput(
        engine_result=engine_result,
        interior_pov=interior_pov,
        gtp_coherence=gtp_coherence,
        context_package=context_package,
        cobalt_retrieval=cobalt_packet,
    )
