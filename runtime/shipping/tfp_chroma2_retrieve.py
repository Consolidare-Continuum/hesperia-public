# HESPERIA — TFP CHROMA-2 retrieve helper (Class B instructor path).
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). See LEGAL_NOTICE.md.

"""Pull allowlisted ``retrieval`` docs from CHROMA-2 (Papra ``documents``).

Corpus SoT for TFP = CHROMA-2 via brain ``agent_mcp_colombo_library`` (profile tfp_ru
filters: lang=ru, theme=psychology). Runtime shipping venv may lack chromadb —
this helper prefers in-process import, else subprocesses the brain colombo-chroma2
venv. Falls back to empty so caller can use inspector_exports.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_DEFAULT_CHROMA2 = "http://chroma-2.prichindel.local:8002"
_DEFAULT_BRAIN = "/data/altitudine/prichindel.com"
_MAX_SNIPPET = 900
_MAX_DOCS = 4


def _chroma2_url() -> str:
    return (
        os.environ.get("HESPERIA_TFP_CHROMA_URL")
        or os.environ.get("CHROMA_SERVER_URL")
        or _DEFAULT_CHROMA2
    ).strip()


def _brain_repo() -> Path:
    raw = (os.environ.get("CURSOR_REPO_ROOT") or os.environ.get("BRAIN_REPO_ROOT") or _DEFAULT_BRAIN).strip()
    return Path(raw)


def _colombo_python() -> str | None:
    candidates = (
        os.environ.get("HESPERIA_COLOMBO_PYTHON", "").strip(),
        str(_brain_repo() / "venv" / "colombo-chroma2" / "bin" / "python"),
        "/data/workspaces/hesperia/.venv/bin/python",
        sys.executable,
    )
    for c in candidates:
        if c and Path(c).is_file():
            return c
    return None


def _cap_docs(docs: list[dict[str, Any]], *, max_docs: int, max_snippet: int) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for d in docs[:max_docs]:
        text = (d.get("text") or d.get("snippet") or "")[:max_snippet]
        out.append(
            {
                "id": str(d.get("doc_id") or d.get("id") or ""),
                "name": str(d.get("doc_name") or d.get("name") or ""),
                "snippet": text,
                "label": "library_evidence",
            }
        )
    return out


def _query_inprocess(query: str, n: int) -> list[dict[str, Any]]:
    brain = _brain_repo()
    if str(brain) not in sys.path:
        sys.path.insert(0, str(brain))
    os.environ.setdefault("CHROMA_SERVER_URL", _chroma2_url())
    from agent_mcp_colombo_library.store import query_library  # type: ignore

    return query_library(query, n_results=n, lang="ru", theme="psychology")


def _query_subprocess(query: str, n: int) -> list[dict[str, Any]]:
    py = _colombo_python()
    brain = _brain_repo()
    if not py or not (brain / "agent_mcp_colombo_library" / "store.py").is_file():
        raise RuntimeError("colombo_chroma2_python_or_brain_missing")
    code = (
        "import json,os,sys\n"
        "os.environ['CHROMA_SERVER_URL']=sys.argv[1]\n"
        "sys.path.insert(0, sys.argv[2])\n"
        "from agent_mcp_colombo_library.store import query_library\n"
        "q=json.load(sys.stdin)['q']; n=int(sys.argv[3])\n"
        "print(json.dumps(query_library(q, n_results=n, lang='ru', theme='psychology'), ensure_ascii=False))\n"
    )
    proc = subprocess.run(
        [py, "-c", code, _chroma2_url(), str(brain), str(n)],
        input=json.dumps({"q": query}, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=int(os.environ.get("HESPERIA_TFP_RETRIEVE_TIMEOUT", "45") or "45"),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "retrieve_failed")[:500])
    data = json.loads(proc.stdout or "[]")
    if not isinstance(data, list):
        raise RuntimeError("retrieve_non_list")
    return data


def retrieve_tfp_library(
    query: str,
    *,
    top_k: int | None = None,
    max_snippet: int | None = None,
) -> dict[str, Any]:
    """Return allowlisted retrieval block for context_packet."""
    n = max(1, min(8, int(top_k if top_k is not None else os.environ.get("HESPERIA_TFP_RETRIEVE_TOP_K", _MAX_DOCS) or _MAX_DOCS)))
    snip = int(max_snippet if max_snippet is not None else _MAX_SNIPPET)
    mode = (os.environ.get("HESPERIA_TFP_RETRIEVAL") or "chroma2").strip().lower()
    if mode in ("off", "0", "false", "no", "inspector", "inspector_only"):
        return {
            "source": "chroma2_skipped",
            "status": "skipped",
            "doc_count": 0,
            "documents": [],
            "chroma_url": _chroma2_url(),
        }
    hits: list[dict[str, Any]] = []
    err: str | None = None
    try:
        try:
            hits = _query_inprocess(query, n)
        except Exception:
            hits = _query_subprocess(query, n)
    except Exception as exc:  # noqa: BLE001 — soft fallback for instructor path
        err = f"{type(exc).__name__}: {exc}"
        hits = []
    docs = _cap_docs(hits, max_docs=n, max_snippet=snip)
    return {
        "source": "chroma-2_colombo_library",
        "status": "ok" if docs else ("unreachable" if err else "empty"),
        "doc_count": len(docs),
        "documents": docs,
        "profile": "tfp_ru",
        "chroma_url": _chroma2_url(),
        "error": err,
        "corpus_home": "chroma-2_colombo_library",
    }


def corpus_snapshot_id_for_retrieval(retrieval: dict[str, Any]) -> str:
    """Stable-ish snapshot id for CHROMA-2 packs (task HES-TFP-100-52)."""
    if retrieval.get("status") == "ok" and retrieval.get("doc_count"):
        ids = sorted(str(d.get("id") or "") for d in (retrieval.get("documents") or []) if d.get("id"))
        digest = "-".join(ids)[:48] if ids else "empty"
        return f"chroma2_tfp_ru_{digest}"
    return "chroma2_tfp_ru_unavailable"
