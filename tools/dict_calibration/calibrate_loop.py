# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Task 9 — Closed-loop iteration: patch → rebuild links → eval → convergence check."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .build_links import build_links, links_to_engine_dict_a
from .errors_extract import extract_errors
from .evaluate import evaluate_on_texts
from .jsonl_util import read_jsonl, write_json, write_jsonl
from .patch_llm import apply_patch_to_links, propose_patch


@dataclass
class LoopConfig:
    max_iters: int = 3
    unmapped_pct_max: float = 25.0
    entropy_delta_max: float = 0.02
    patch_max_errors: int = 80
    patch_max_links: int = 40


def run_iteration(
    work: Path,
    *,
    normalized_rows: list[dict[str, Any]],
    anchored_rows: list[dict[str, Any]],
    eval_texts: list[str],
    dict_b_paths: list[Path],
    anchors_path: Path,
    links_path: Path,
    dict_a_engine_path: Path,
    prev_entropy: float | None,
    cfg: LoopConfig,
) -> dict[str, Any]:
    links = build_links(normalized_rows, anchored_rows)
    write_jsonl(links_path, links)
    write_jsonl(dict_a_engine_path, links_to_engine_dict_a(links))

    ev = evaluate_on_texts(
        eval_texts,
        dict_a_path=dict_a_engine_path,
        dict_b_paths=dict_b_paths,
        anchors_path=anchors_path,
    )
    write_json(work / "evaluation_run.json", ev)

    err = extract_errors(ev, eval_texts)
    write_jsonl(work / "dict_errors.jsonl", err)

    ent = float(ev.get("aggregate", {}).get("concept_entropy") or 0)
    um = float(ev.get("aggregate", {}).get("unmapped_lexical_pct_mean") or 0)

    converged = um < cfg.unmapped_pct_max
    if prev_entropy is not None:
        converged = converged and abs(ent - prev_entropy) < cfg.entropy_delta_max

    patch: dict[str, Any] = {}
    if not converged and err:
        patch = propose_patch(
            err,
            links,
            max_errors=cfg.patch_max_errors,
            max_links=cfg.patch_max_links,
        )
        write_json(work / "dict_patch.json", patch)
        if any(patch.get(k) for k in ("add_lexical", "adjust_priorities", "merge_concepts", "split_concepts")):
            links = apply_patch_to_links(links, patch)
            write_jsonl(work / "dict_a_to_b_links_patched.jsonl", links)
            write_jsonl(dict_a_engine_path, links_to_engine_dict_a(links))

    return {
        "concept_entropy": ent,
        "unmapped_lexical_pct_mean": um,
        "converged": converged,
        "patch_applied": bool(patch),
    }
