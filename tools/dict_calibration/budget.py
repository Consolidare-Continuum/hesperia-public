# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Caps for frugal OpenAI use (gpt-4o-mini); full TFP pass stays deterministic offline."""

from __future__ import annotations

from typing import Any

# One ``run-all --budget`` ≈ low tens of API calls; well under typical small credit lines
# if you avoid re-running normalize on huge candidate dumps.
BUDGET = {
    "min_freq": 4,
    "normalize_max_rows": 240,
    "normalize_batch_size": 16,
    "propose_limit_cap": 100,
    "max_concepts_cap": 48,
    "catalog_limit": 100,
    "propose_batch_size": 28,
    "patch_max_errors": 28,
    "patch_max_links": 22,
    "eval_max_files": 4,
    "eval_max_chars": 6000,
    "loop_max_iters_cap": 1,
}


def apply_run_all_budget(ns: Any) -> Any:
    ns.min_freq = max(int(ns.min_freq), BUDGET["min_freq"])
    cap = BUDGET["normalize_max_rows"]
    mr = getattr(ns, "normalize_max_rows", None)
    if mr is None:
        ns.normalize_max_rows = cap
    else:
        ns.normalize_max_rows = min(int(mr), cap)
    ns.batch_size = min(int(ns.batch_size), BUDGET["normalize_batch_size"])
    ns.propose_limit = min(int(ns.propose_limit), BUDGET["propose_limit_cap"])
    ns.max_concepts = min(int(ns.max_concepts), BUDGET["max_concepts_cap"])
    ns.catalog_limit = min(int(ns.catalog_limit), BUDGET["catalog_limit"])
    ns.propose_batch_size = min(int(ns.propose_batch_size), BUDGET["propose_batch_size"])
    ns.patch_max_errors = min(int(ns.patch_max_errors), BUDGET["patch_max_errors"])
    ns.patch_max_links = min(int(ns.patch_max_links), BUDGET["patch_max_links"])
    ns.eval_max_files = min(int(ns.eval_max_files), BUDGET["eval_max_files"])
    ns.eval_max_chars = min(int(ns.eval_max_chars), BUDGET["eval_max_chars"])
    return ns
