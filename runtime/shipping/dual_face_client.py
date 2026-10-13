# HESPERIA — Dual-face HTTP clients (core :18880 / TFP :18881).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Shared client helper for side-by-side Class A / Class B lanes (HES-TFP-100-17)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _url(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


class HesperiaFaceClient:
    """Minimal JSON client for one analyze face."""

    def __init__(self, base_url: str, *, face: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.face = face
        self.timeout = timeout

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            _url(self.base_url, path),
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"raw": raw[:800]}
            raise RuntimeError(f"{self.face} HTTP {exc.code}: {payload}") from exc

    def health(self) -> dict[str, Any]:
        req = urllib.request.Request(_url(self.base_url, "/health"), method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def analyze(self, text: str, **extra: Any) -> dict[str, Any]:
        body = {"text": text, **extra}
        return self._post("/analyze", body)

    def interpret(
        self,
        text: str,
        *,
        mode: str = "deterministic",
        context_packet: dict[str, Any] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"text": text, "mode": mode, **extra}
        if context_packet is not None:
            body["context_packet"] = context_packet
        return self._post("/product/interpret", body)


def CoreClient(base_url: str | None = None, **kwargs: Any) -> HesperiaFaceClient:
    url = (base_url or os.environ.get("HESPERIA_CORE_URL") or "http://127.0.0.1:18880").strip()
    return HesperiaFaceClient(url, face="core", **kwargs)


def TfpClient(base_url: str | None = None, **kwargs: Any) -> HesperiaFaceClient:
    url = (base_url or os.environ.get("HESPERIA_TFP_URL") or "http://127.0.0.1:18881").strip()
    return HesperiaFaceClient(url, face="tfp", **kwargs)
