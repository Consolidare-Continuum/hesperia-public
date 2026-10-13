#!/usr/bin/env python3
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OPENAI_MODEL = os.environ.get("HESPERIA_OPENAI_MODEL", os.environ.get("HESPERIA_LLM_INTERPRET_MODEL", "gpt-4o-mini"))


def log_stderr(message: str) -> None:
    """Line to stderr, flushed (visible under `tee` when merged with stdout)."""
    print(message, file=sys.stderr, flush=True)


def log_tool_banner(tool: str, **parts: Any) -> None:
    bits = " ".join(f"{k}={v}" for k, v in parts.items())
    log_stderr(f"[{tool}] start {bits}")


def log_tool_progress(tool: str, index: int, total: int, *, every: int, detail: str = "") -> None:
    if total <= 0 or every <= 0:
        return
    if index % every != 0 and index != total:
        return
    tail = f" | {detail}" if detail else ""
    log_stderr(f"[{tool}] progress {index}/{total}{tail}")


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    rows: list[dict[str, Any]] = []
    for i, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        s = raw.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSONL at {p}:{i}: {e}") from e
        if not isinstance(obj, dict):
            raise ValueError(f"JSONL row must be an object at {p}:{i}")
        rows.append(obj)
    return rows


def save_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def cosine(a: Iterable[float], b: Iterable[float]) -> float:
    av = list(a)
    bv = list(b)
    if len(av) != len(bv):
        raise ValueError("cosine(): vector length mismatch")
    dot = sum(x * y for x, y in zip(av, bv, strict=True))
    na = math.sqrt(sum(x * x for x in av))
    nb = math.sqrt(sum(y * y for y in bv))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(dot / (na * nb))


def softmax(x: Iterable[float], temperature: float = 1.0) -> list[float]:
    xs = list(x)
    if not xs:
        return []
    if temperature <= 0:
        raise ValueError("softmax(): temperature must be > 0")
    m = max(xs)
    exps = [math.exp((v - m) / temperature) for v in xs]
    z = sum(exps)
    if z == 0.0:
        return [0.0 for _ in xs]
    return [float(v / z) for v in exps]


def ema(series: Iterable[float], alpha: float) -> list[float]:
    if not (0.0 < alpha <= 1.0):
        raise ValueError("ema(): alpha must be in (0, 1]")
    out: list[float] = []
    acc: float | None = None
    for v in series:
        if acc is None:
            acc = float(v)
        else:
            acc = alpha * float(v) + (1.0 - alpha) * acc
        out.append(acc)
    return out


def timestamp_dir(base: str | Path = "calibration_runs") -> Path:
    b = Path(base)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = b / ts
    out.mkdir(parents=True, exist_ok=True)
    return out


@dataclass(frozen=True)
class StructuredCall:
    model: str = DEFAULT_OPENAI_MODEL
    reasoning_effort: str = "none"
    max_output_tokens: int = 2000


def call_structured(prompt: str, schema: dict[str, Any], *, cfg: StructuredCall = StructuredCall()) -> Any:
    """
    Deterministic JSON-only call (temperature=0) using Responses API with JSON Schema.

    Requires OPENAI_API_KEY in the environment.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY")

    from openai import OpenAI  # local import keeps CLI tools importable without deps

    client = OpenAI()
    request: dict[str, Any] = {
        "model": cfg.model,
        "temperature": 0,
        "max_output_tokens": cfg.max_output_tokens,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "calibration_schema",
                "schema": schema,
                "strict": True,
            }
        },
        "input": prompt,
    }
    if cfg.reasoning_effort:
        request["reasoning"] = {"effort": cfg.reasoning_effort}

    resp = client.responses.create(
        **request,
    )
    try:
        return json.loads(resp.output_text)
    except Exception as e:
        raise RuntimeError(f"OpenAI returned non-JSON output: {resp.output_text[:500]}") from e
