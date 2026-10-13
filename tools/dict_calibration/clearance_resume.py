# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Resumable normalize + propose for large clearance runs (checkpoint + batch audit)."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tools.dict_calibration.anchor_bind import load_anchor_registry, load_merged_dict_b
from tools.dict_calibration.build_links import build_links, links_to_engine_dict_a
from tools.dict_calibration.errors_extract import extract_errors
from tools.dict_calibration.evaluate import evaluate_on_texts
from tools.dict_calibration.env_defaults import (
    assert_domain_corpus_pairing,
    normalize_domain,
)
from tools.dict_calibration.extract_lexical import extract_corpus
from tools.dict_calibration.jsonl_util import append_jsonl, read_jsonl, write_json, write_jsonl
from tools.dict_calibration.lexical_filter import filter_rows_for_llm
from tools.dict_calibration.normalize_llm import normalize_batch
from tools.dict_calibration.propose_llm import (
    call_propose_chunk,
    merge_concept_rows_into_state,
    _catalog_rows,
)
from tools.dict_calibration.run_pipeline import _default_engine_paths

_REPO = Path(__file__).resolve().parents[2]


def clearance_dir(workdir: Path) -> Path:
    d = workdir / ".clearance"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(msg: str, log_every_stderr: Callable[[str], None] | None) -> None:
    if log_every_stderr:
        log_every_stderr(msg)
    else:
        print(msg, file=sys.stderr)


def run_extract(*, corpus: Path, workdir: Path, min_freq: int) -> dict[str, Any]:
    workdir.mkdir(parents=True, exist_ok=True)
    rows = extract_corpus(corpus, min_freq=min_freq)
    write_jsonl(workdir / "dict_a_candidates.jsonl", rows)
    write_json(
        clearance_dir(workdir) / "extract_meta.json",
        {
            "corpus": str(corpus),
            "min_freq": min_freq,
            "candidates_count": len(rows),
            "updated_at": _now_iso(),
        },
    )
    return {"candidates_count": len(rows)}


def run_normalize_resume(
    workdir: Path,
    *,
    batch_size: int = 24,
    dry_run: bool = False,
    max_rows: int | None = None,
    log_every: int = 25,
    log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    w = workdir.resolve()
    cd = clearance_dir(w)
    cand_path = w / "dict_a_candidates.jsonl"
    if not cand_path.is_file():
        raise FileNotFoundError(f"missing {cand_path}; run extract first")
    rows = read_jsonl(cand_path)
    filtered = filter_rows_for_llm(rows, max_rows=None)
    if max_rows is not None and max_rows > 0:
        filtered = filtered[: int(max_rows)]
    n_total = len(filtered)
    norm_path = w / "dict_a_normalized.jsonl"
    state_path = cd / "normalize_state.json"
    complete_path = cd / "normalize_complete.json"

    start = 0
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        start = int(state.get("next_row_index", 0))
        if norm_path.is_file():
            existing = read_jsonl(norm_path)
            if len(existing) != start:
                raise ValueError(
                    f"normalize checkpoint mismatch: state next_row_index={start} but "
                    f"{norm_path.name} has {len(existing)} lines (repair or reset-normalize)"
                )
    elif norm_path.is_file() and norm_path.stat().st_size > 0:
        raise ValueError(
            f"{norm_path} exists without {state_path.name} — use reset-normalize or a fresh WORKDIR"
        )
    else:
        if norm_path.exists():
            norm_path.unlink()

    calls_done = ((start + batch_size - 1) // batch_size) if batch_size and start else 0
    calls_total = (n_total + batch_size - 1) // batch_size if n_total else 0
    t0 = time.perf_counter()

    for i in range(start, n_total, batch_size):
        chunk = filtered[i : i + batch_size]
        if dry_run:
            out_chunk = [dict(r, normalized=str(r.get("text", "")), variants=[]) for r in chunk]
        else:
            out_chunk = normalize_batch(chunk, batch_size=len(chunk))
        append_jsonl(norm_path, out_chunk)
        new_next = i + len(chunk)
        write_json(
            state_path,
            {
                "next_row_index": new_next,
                "filtered_total": n_total,
                "batch_size": batch_size,
                "dry_run": dry_run,
                "updated_at": _now_iso(),
            },
        )
        calls_done += 1
        if log_every > 0 and calls_done % log_every == 0:
            pct = 100.0 * new_next / max(1, n_total)
            elapsed = time.perf_counter() - t0
            _log(
                f"[normalize] rows {new_next}/{n_total} ({pct:.1f}%) "
                f"api_chunks ~{calls_done}/{calls_total} elapsed={elapsed:.0f}s",
                log,
            )

    write_json(complete_path, {"ok": True, "filtered_total": n_total, "at": _now_iso()})
    _log(
        f"[normalize] done rows={n_total} api_chunks≈{calls_total} → {norm_path}",
        log,
    )
    return {"filtered_total": n_total, "normalize_path": str(norm_path)}


def _replay_propose_batches(batches_path: Path) -> tuple[list[dict[str, Any]], set[str]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    if not batches_path.is_file():
        return merged, seen
    for line in batches_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        arr = obj.get("concepts")
        if isinstance(arr, list):
            merge_concept_rows_into_state(arr, merged, seen)
    return merged, seen


def run_propose_resume(
    workdir: Path,
    *,
    dict_b_paths: list[Path] | None,
    max_concepts: int = 80,
    batch_size: int = 40,
    catalog_limit: int = 400,
    dry_run: bool = False,
    max_phrases: int | None = None,
    log_every: int = 25,
    log: Callable[[str], None] | None = None,
    domain: str = "core",
) -> dict[str, Any]:
    w = workdir.resolve()
    cd = clearance_dir(w)
    domain = (domain or "core").strip().lower()
    if domain not in {"core", "tfp"}:
        raise ValueError(f"domain must be 'core' or 'tfp', got {domain!r}")
    norm_path = w / "dict_a_normalized.jsonl"
    if not norm_path.is_file():
        raise FileNotFoundError(f"missing {norm_path}; finish normalize first")
    norm_rows = read_jsonl(norm_path)
    phrases_all = [str(r.get("normalized") or r.get("text", "")).strip() for r in norm_rows]
    phrases_all = [p for p in phrases_all if p]

    db_paths, _ = _default_engine_paths(_REPO, domain=domain)
    if dict_b_paths:
        db_paths = list(dict_b_paths)
    merged_b = load_merged_dict_b(db_paths)
    catalog = _catalog_rows(merged_b, limit=catalog_limit, domain=domain)  # type: ignore[arg-type]
    _log(
        f"[propose] domain={domain} catalog_rows={len(merged_b)} "
        f"dict_b={[str(p) for p in db_paths]}",
        log,
    )

    batches_path = cd / "propose_batches.jsonl"
    state_path = cd / "propose_state.json"
    complete_path = cd / "propose_complete.json"
    draft_path = w / "dict_b_draft.jsonl"

    norm_complete = cd / "normalize_complete.json"
    if not norm_complete.is_file():
        raise ValueError("normalize not finished (.clearance/normalize_complete.json missing)")
    nst_path = cd / "normalize_state.json"
    if nst_path.is_file():
        nst = json.loads(nst_path.read_text(encoding="utf-8"))
        if int(nst.get("next_row_index", -1)) != int(nst.get("filtered_total", -2)):
            raise ValueError("normalize incomplete (next_row_index != filtered_total in normalize_state.json)")

    phrases: list[str]
    if state_path.is_file():
        st0 = json.loads(state_path.read_text(encoding="utf-8"))
        prev_domain = str(st0.get("domain") or "").strip().lower()
        if prev_domain and prev_domain != domain:
            raise ValueError(
                f"propose_state domain={prev_domain!r} != requested domain={domain!r}; "
                "run reset-propose before switching domain (contaminated checkpoints must not resume)"
            )
        if not prev_domain and domain == "core":
            # Legacy checkpoint written before domain was recorded — treat as unsafe for core.
            raise ValueError(
                "propose_state.json has no domain field (pre-fix TFP-default era). "
                "Run reset-propose, then re-propose with --domain core"
            )
        ptot = int(st0.get("phrase_total", 0))
        if ptot <= 0:
            raise ValueError("invalid propose_state: phrase_total")
        if len(phrases_all) < ptot:
            raise ValueError(
                "normalized jsonl shorter than propose phrase_total; repair or reset-propose"
            )
        phrases = phrases_all[:ptot]
    else:
        phrases = list(phrases_all)
        if max_phrases is not None and max_phrases > 0:
            phrases = phrases[: int(max_phrases)]
    n_total = len(phrases)

    start = 0
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    if state_path.is_file():
        st = json.loads(state_path.read_text(encoding="utf-8"))
        start = int(st.get("next_phrase_index", 0))
        merged, seen = _replay_propose_batches(batches_path)
        if start > 0 and not batches_path.is_file():
            raise ValueError("propose_state exists but propose_batches.jsonl missing")
        last_chunk_end = 0
        if batches_path.is_file():
            for line in batches_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                last_chunk_end = int(obj.get("chunk_end", 0))
        if start > 0 and last_chunk_end != start:
            raise ValueError(
                f"propose checkpoint mismatch: next_phrase_index={start} but last batch chunk_end={last_chunk_end}"
            )
    elif batches_path.is_file() and batches_path.stat().st_size > 0:
        raise ValueError(f"{batches_path} exists without propose_state.json — use reset-propose")
    else:
        if batches_path.exists():
            batches_path.unlink()

    calls_done = ((start + batch_size - 1) // batch_size) if batch_size and start else 0
    calls_total = (n_total + batch_size - 1) // batch_size if n_total else 0
    t0 = time.perf_counter()

    for i in range(start, n_total, batch_size):
        chunk = phrases[i : i + batch_size]
        chunk_end = i + len(chunk)
        if dry_run:
            arr = (
                [
                    {
                        "concept_id": "dry_run.placeholder",
                        "labels": ["placeholder"],
                        "from_lexical": [chunk[0]] if chunk else [],
                        "confidence": 0.1,
                    }
                ]
                if chunk
                else []
            )
        else:
            arr = call_propose_chunk(chunk, catalog, max_concepts=max_concepts, domain=domain)  # type: ignore[arg-type]
        rec = {"chunk_start": i, "chunk_end": chunk_end, "concepts": arr, "domain": domain}
        append_jsonl(batches_path, [rec])
        merge_concept_rows_into_state(arr, merged, seen)
        write_json(
            state_path,
            {
                "next_phrase_index": chunk_end,
                "phrase_total": n_total,
                "batch_size": batch_size,
                "max_concepts": max_concepts,
                "catalog_limit": catalog_limit,
                "domain": domain,
                "dry_run": dry_run,
                "draft_concepts_so_far": len(merged),
                "updated_at": _now_iso(),
            },
        )
        calls_done += 1
        if log_every > 0 and calls_done % log_every == 0:
            pct = 100.0 * chunk_end / max(1, n_total)
            elapsed = time.perf_counter() - t0
            _log(
                f"[propose] phrases {chunk_end}/{n_total} ({pct:.1f}%) "
                f"api_chunks ~{calls_done}/{calls_total} unique_concepts={len(merged)} elapsed={elapsed:.0f}s",
                log,
            )

    write_jsonl(draft_path, merged)
    write_json(complete_path, {"ok": True, "phrase_total": n_total, "draft_concepts": len(merged), "at": _now_iso()})
    _log(
        f"[propose] done phrases={n_total} api_chunks≈{calls_total} draft_concepts={len(merged)} → {draft_path}",
        log,
    )
    return {"phrase_total": n_total, "draft_concepts": len(merged), "draft_path": str(draft_path)}


def run_post(
    workdir: Path,
    *,
    corpus: Path,
    min_score: float = 0.52,
    dict_b_paths: list[Path] | None = None,
    eval_max_files: int = 0,
    eval_max_chars: int = 0,
    anchor_workers: int = 1,
    domain: str = "core",
) -> None:
    from tools.dict_calibration.run_pipeline import cmd_anchor, cmd_errors, cmd_eval, cmd_links

    import argparse

    workdir = workdir.resolve()
    w = str(workdir)
    domain = normalize_domain(domain)
    dbp = dict_b_paths
    assert_domain_corpus_pairing(domain, corpus, dict_b_paths=dbp)
    propose_state_path = workdir / ".clearance" / "propose_state.json"
    if not propose_state_path.is_file():
        raise ValueError(
            "missing .clearance/propose_state.json; post-processing requires "
            "a domain-bound propose checkpoint"
        )
    propose_state = json.loads(propose_state_path.read_text(encoding="utf-8"))
    propose_domain = str(propose_state.get("domain") or "").strip().lower()
    if propose_domain != domain:
        raise ValueError(
            f"propose_state domain={propose_domain!r} != requested "
            f"domain={domain!r}; post-processing cannot cross domains"
        )
    cmd_anchor(
        argparse.Namespace(
            workdir=w,
            dict_b=dbp,
            domain=domain,
            min_score=min_score,
            anchor_workers=int(anchor_workers or 1),
        )
    )
    cmd_links(argparse.Namespace(workdir=w))
    cmd_eval(
        argparse.Namespace(
            workdir=w,
            corpus=str(corpus),
            texts_file=None,
            dict_b=dbp,
            domain=domain,
            eval_max_files=eval_max_files,
            eval_max_chars=eval_max_chars,
        )
    )
    cmd_errors(
        argparse.Namespace(
            workdir=w,
            corpus=str(corpus),
            texts_file=None,
            eval_max_files=eval_max_files,
            eval_max_chars=eval_max_chars,
        )
    )


def clearance_status(workdir: Path) -> dict[str, Any]:
    w = workdir.resolve()
    cd = w / ".clearance"
    out: dict[str, Any] = {"workdir": str(w)}

    cands = w / "dict_a_candidates.jsonl"
    if cands.is_file():
        n = sum(1 for _ in cands.open(encoding="utf-8") if _.strip())
        out["dict_a_candidates_lines"] = n
    else:
        out["dict_a_candidates_lines"] = 0

    ext_meta = cd / "extract_meta.json"
    if ext_meta.is_file():
        out["extract"] = json.loads(ext_meta.read_text(encoding="utf-8"))

    norm_st = cd / "normalize_state.json"
    norm_done = cd / "normalize_complete.json"
    norm_path = w / "dict_a_normalized.jsonl"
    if norm_st.is_file():
        st = json.loads(norm_st.read_text(encoding="utf-8"))
        total = int(st.get("filtered_total", 0))
        nxt = int(st.get("next_row_index", 0))
        out["normalize"] = {
            "next_row_index": nxt,
            "filtered_total": total,
            "progress_pct": round(100.0 * nxt / total, 2) if total else 0.0,
            "complete": norm_done.is_file(),
            "batch_size": st.get("batch_size"),
        }
        bs = int(st.get("batch_size") or 24)
        out["normalize"]["api_chunks_done_approx"] = (nxt + bs - 1) // bs if total else 0
        out["normalize"]["api_chunks_total_approx"] = (total + bs - 1) // bs if total else 0
    elif norm_path.is_file():
        nl = sum(1 for _ in norm_path.open(encoding="utf-8") if _.strip())
        out["normalize"] = {"note": "jsonl exists without normalize_state.json", "lines": nl}
    else:
        out["normalize"] = {"note": "not started"}

    prop_st = cd / "propose_state.json"
    prop_done = cd / "propose_complete.json"
    batches = cd / "propose_batches.jsonl"
    if prop_st.is_file():
        st = json.loads(prop_st.read_text(encoding="utf-8"))
        total = int(st.get("phrase_total", 0))
        nxt = int(st.get("next_phrase_index", 0))
        out["propose"] = {
            "next_phrase_index": nxt,
            "phrase_total": total,
            "progress_pct": round(100.0 * nxt / total, 2) if total else 0.0,
            "complete": prop_done.is_file(),
            "draft_concepts_so_far": st.get("draft_concepts_so_far"),
            "batch_size": st.get("batch_size"),
        }
        bs = int(st.get("batch_size") or 40)
        out["propose"]["api_chunks_done_approx"] = (nxt + bs - 1) // bs if total else 0
        out["propose"]["api_chunks_total_approx"] = (total + bs - 1) // bs if total else 0
    elif batches.is_file() and batches.stat().st_size > 0:
        out["propose"] = {"note": "propose_batches.jsonl without state — repair or reset-propose"}
    else:
        out["propose"] = {"note": "not started"}

    out["files"] = {
        "dict_b_draft": (w / "dict_b_draft.jsonl").is_file(),
        "dict_b_anchored": (w / "dict_b_anchored.jsonl").is_file(),
        "dict_a_to_b_links": (w / "dict_a_to_b_links.jsonl").is_file(),
        "evaluation_run": (w / "evaluation_run.json").is_file(),
        "dict_errors": (w / "dict_errors.jsonl").is_file(),
    }
    return out


def reset_normalize(workdir: Path) -> None:
    w = workdir.resolve()
    cd = clearance_dir(w)
    for p in (w / "dict_a_normalized.jsonl", cd / "normalize_state.json", cd / "normalize_complete.json"):
        if p.exists():
            p.unlink()


def reset_propose(workdir: Path) -> None:
    w = workdir.resolve()
    cd = clearance_dir(w)
    for p in (
        w / "dict_b_draft.jsonl",
        cd / "propose_state.json",
        cd / "propose_complete.json",
        cd / "propose_batches.jsonl",
    ):
        if p.exists():
            p.unlink()
