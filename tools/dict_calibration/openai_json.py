# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


def calib_mock_openai() -> bool:
    """When true, ``chat_json`` never calls the network (CI / wiring / dry runs)."""
    v = os.environ.get("HESPERIA_CALIB_MOCK_OPENAI", "").strip().lower()
    return v in ("1", "true", "yes")


def _mock_normalize_from_user(user: str) -> dict[str, Any]:
    idx = user.find("Input:\n")
    if idx < 0:
        return {"items": []}
    rest = user[idx + len("Input:\n") :].strip()
    blob = rest.split("\n\n")[0].strip()
    try:
        payload = json.loads(blob)
    except json.JSONDecodeError:
        return {"items": []}
    if not isinstance(payload, list):
        return {"items": []}
    items: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("row_id", ""))
        st = str(row.get("text", ""))
        items.append(
            {
                "row_id": rid,
                "source_text": st,
                "normalized": st.strip().lower(),
                "variants": [],
            }
        )
    return {"items": items}


def _mock_catalog_lookup(user: str) -> list[tuple[str, str]]:
    """Parse catalog lines from propose prompts (``- id: label`` or ``id — label``)."""
    rows: list[tuple[str, str]] = []
    for line in user.splitlines():
        line = line.strip().lstrip("-•* ").strip()
        if not line:
            continue
        cid = ""
        lab = ""
        if ": " in line and (line.startswith("core.") or line.startswith("tfp.") or "core." in line[:40]):
            # ``core.good.altruism: Altruism [GOOD/Altruism]``
            left, _, right = line.partition(": ")
            cid = left.strip()
            lab = right.split("[", 1)[0].strip()
        elif " — " in line or " - " in line:
            sep = " — " if " — " in line else " - "
            left, _, right = line.partition(sep)
            cid = left.strip()
            lab = right.strip()
        if cid.startswith("core.") or cid.startswith("tfp.") or cid.startswith("mock."):
            rows.append((cid, lab or cid.rsplit(".", 1)[-1]))
    return rows


def _mock_best_concept_id(phrase: str, catalog: list[tuple[str, str]]) -> tuple[str, float]:
    """Deterministic nearest catalog id (label/id substring); else mock placeholder."""
    p = phrase.strip().lower()
    if not p:
        return "mock.lexical.placeholder", 0.0
    best_id = "mock.lexical.placeholder"
    best = 0.0
    for cid, lab in catalog:
        for cand in (lab.lower(), cid.lower().rsplit(".", 1)[-1].replace("_", " ")):
            if not cand:
                continue
            if p == cand or p in cand or cand in p:
                score = 0.92 if p == cand else 0.75
            else:
                score = SequenceMatcher(None, p, cand).ratio()
            if score > best:
                best = score
                best_id = cid
    if best < 0.45:
        return "mock.lexical.placeholder", best
    return best_id, best


def _mock_propose_from_user(user: str) -> dict[str, Any]:
    markers = (
        "Normalized lexical items:\n",
        "Lexical items from the corpus:\n",
    )
    idx = -1
    marker_used = ""
    for marker in markers:
        idx = user.find(marker)
        if idx >= 0:
            marker_used = marker
            break
    if idx < 0:
        return {"concepts": []}
    rest = user[idx + len(marker_used) :]
    end = rest.find("\n\nReturn")
    if end < 0:
        blob = rest.strip()
    else:
        blob = rest[:end].strip()
    try:
        chunk = json.loads(blob)
    except json.JSONDecodeError:
        return {"concepts": []}
    if not isinstance(chunk, list) or not chunk:
        return {"concepts": []}
    mc_m = re.search(r"Cap total concepts at (\d+)", user)
    cap = int(mc_m.group(1)) if mc_m else 80
    catalog = _mock_catalog_lookup(user)
    concepts: list[dict[str, Any]] = []
    for ph in chunk[:cap]:
        if not str(ph).strip():
            continue
        p = str(ph).strip()
        cid, score = _mock_best_concept_id(p, catalog)
        concepts.append(
            {
                "concept_id": cid,
                "labels": [p[:48]],
                "from_lexical": [p],
                "confidence": round(max(0.5, min(0.95, score if score else 0.5)), 3),
            }
        )
    return {"concepts": concepts}


def _mock_chat_json(user: str) -> Any:
    """Deterministic stand-in payloads so calibration code runs without OpenAI."""
    if '"add_lexical"' in user or ("Errors:" in user and "Return JSON patch" in user):
        return {
            "add_lexical": [],
            "merge_concepts": [],
            "split_concepts": [],
            "adjust_priorities": [],
            "notes": "HESPERIA_CALIB_MOCK_OPENAI",
        }
    if (
        ("Normalized lexical items:" in user or "Lexical items from the corpus:" in user)
        and "Return JSON:" in user
        and "concepts" in user
    ):
        return _mock_propose_from_user(user)
    if "Input:\n" in user and ("items" in user or "source_text" in user):
        return _mock_normalize_from_user(user)
    if "Corpus phrases" in user and "links" in user:
        return {"links": []}
    if (
        "entries" in user
        and "marker" in user.lower()
        and ("return json" in user.lower())
    ):
        return {"entries": []}
    return {}


def load_repo_dotenv() -> None:
    """Load repo-root ``.env`` if present (gitignored); does not override existing env vars."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def get_client():
    try:
        from openai import OpenAI
    except ImportError as e:
        raise ImportError("Install OpenAI SDK: pip install openai") from e
    load_repo_dotenv()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=key)


def require_openai_key() -> None:
    """Load repo ``.env`` then fail fast if the key is missing."""
    if calib_mock_openai():
        return
    load_repo_dotenv()
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError("OPENAI_API_KEY not set — add to repo .env or export in shell")


_LEDGER_DEFAULT = Path(__file__).resolve().parents[2] / "outputs" / "openai_call_ledger.jsonl"


def _ledger_path() -> Path:
    """Where every ``chat_json`` call gets appended, durably, one line per call.

    Rule: docs/conventions/API-CALL-DURABILITY.md -- any code that calls a paid/rate-limited
    API in a loop must persist each call's result before moving to the next one, so a crash
    only ever costs the in-progress call, not the whole run. Override per-run with
    ``HESPERIA_CALIB_CALL_LEDGER`` (e.g. point it at the run's own workdir) -- unset falls back
    to a single repo-wide ledger, which is still durable, just less organized per-run.
    """
    raw = os.environ.get("HESPERIA_CALIB_CALL_LEDGER", "").strip()
    return Path(raw) if raw else _LEDGER_DEFAULT


def _append_ledger(*, model: str, call_tag: str | None, user_preview: str, content: str, usage: Any) -> None:
    path = _ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "call_tag": call_tag,
        "user_preview": user_preview[:200],
        "content": content,
        "usage": usage.model_dump() if hasattr(usage, "model_dump") else usage,
    }
    # Open-write-flush-close per call, not a held-open handle: the whole point is surviving a
    # kill between calls, so nothing here can be buffered past the call it belongs to.
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _is_reasoning_family(model: str) -> bool:
    """gpt-5 / o1 / o3 / o4 -- reasoning-tuned models with stricter Chat Completions params
    (e.g. temperature locked to the default 1; max_completion_tokens instead of max_tokens)."""
    return (model or "").lower().startswith(("gpt-5", "o1", "o3", "o4"))


def _chat_completion_limit_kwargs(model: str, mt: int) -> dict[str, int]:
    """
    Some Chat Completions models reject ``max_tokens`` and require ``max_completion_tokens``.

    Override: ``HESPERIA_CALIB_USE_MAX_COMPLETION_TOKENS=1|0`` (force new vs legacy param).
    """
    flag = os.environ.get("HESPERIA_CALIB_USE_MAX_COMPLETION_TOKENS", "").strip().lower()
    if flag in ("1", "true", "yes"):
        return {"max_completion_tokens": mt}
    if flag in ("0", "false", "no"):
        return {"max_tokens": mt}
    if _is_reasoning_family(model):
        return {"max_completion_tokens": mt}
    return {"max_tokens": mt}


def chat_json(
    *,
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.15,
    max_tokens: int | None = None,
    call_tag: str | None = None,
) -> Any:
    """Return parsed JSON from model (json_object mode). Large payloads: raise ``HESPERIA_CALIB_MAX_OUTPUT_TOKENS``.

    Every call -- success or JSON-parse failure -- is appended to the call ledger (see
    ``_ledger_path``) before this function returns or raises, durably, one line per call. This is
    the repo-wide "save each call" rule (docs/conventions/API-CALL-DURABILITY.md): a crash between
    calls costs at most the in-progress call, never the accumulated work of a whole run.
    ``call_tag`` is an optional caller-supplied label (e.g. "pass2/concept_batch5/phrase_chunk3")
    to make the ledger easier to read; omit it and a prompt preview is used instead.
    """
    if calib_mock_openai():
        return _mock_chat_json(user)

    client = get_client()
    model = model or os.environ.get("HESPERIA_CALIB_OPENAI_MODEL", "gpt-4o-mini")
    env_mt = os.environ.get("HESPERIA_CALIB_MAX_OUTPUT_TOKENS", "").strip()
    mt = max_tokens
    if mt is None:
        mt = int(env_mt) if env_mt.isdigit() else 16384
    limit_kw = _chat_completion_limit_kwargs(model, mt)
    temp_kw: dict[str, float] = {} if _is_reasoning_family(model) else {"temperature": temperature}
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **temp_kw,
        **limit_kw,
    )
    content = (resp.choices[0].message.content or "").strip()
    _append_ledger(
        model=model,
        call_tag=call_tag,
        user_preview=user,
        content=content,
        usage=resp.usage,
    )
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        # Do not issue a second HTTP request with the same (often huge) ``user`` blob: it can fail
        # with 400 "could not parse the JSON body" on the wire, and ru-tfp-align bisection is the
        # correct recovery (smaller phrase batches / higher max_tokens on caller side).
        preview = (content[:240] + "…") if len(content) > 240 else content
        raise RuntimeError(
            f"OpenAI returned non-JSON or truncated JSON ({e!s}); split workload or raise "
            f"HESPERIA_CALIB_MAX_OUTPUT_TOKENS. assistant_preview={preview!r}"
        ) from e
