# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Task 5 — Deterministic Dict A ↔ Dict B link table."""

from __future__ import annotations

import os
from difflib import SequenceMatcher
from typing import Any


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.casefold(), b.casefold()).ratio()


def _links_fuzzy_enabled(n_norm: int, n_lex: int) -> bool:
    """
    Full fuzzy scan is O(n_norm * n_lex) SequenceMatcher calls — unusable at clearance scale.

    Default: skip fuzzy when the product exceeds a safe bound. Override:
      HESPERIA_CALIB_LINKS_FUZZY=1  force on (slow)
      HESPERIA_CALIB_LINKS_SKIP_FUZZY=1  force off
    """
    env_off = os.environ.get("HESPERIA_CALIB_LINKS_SKIP_FUZZY", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    env_on = os.environ.get("HESPERIA_CALIB_LINKS_FUZZY", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if env_off:
        return False
    if env_on:
        return True
    # ~200k * ~70k ≈ 14B inner iterations — disable unless user forces fuzzy.
    return n_norm * n_lex <= 25_000_000


def build_links(
    normalized_rows: list[dict[str, Any]],
    anchored_rows: list[dict[str, Any]],
    *,
    fuzzy: bool | None = None,
) -> list[dict[str, Any]]:
    """
    Map lexical strings to anchored ``concept_id`` using ``from_lexical`` lists
    and normalized / variant strings.
    """
    lexical_to_concept: dict[str, tuple[str, str, float]] = {}
    for row in anchored_rows:
        cid = str(row.get("concept_id", ""))
        fl = list(row.get("calibration_from_lexical") or row.get("from_lexical") or [])
        for lx in fl:
            lx = str(lx).strip()
            if lx and lx not in lexical_to_concept:
                lexical_to_concept[lx] = (cid, "exact", 1.0)

    n_lex = len(lexical_to_concept)
    n_norm = sum(
        1
        for r in normalized_rows
        if str(r.get("normalized") or r.get("text", "")).strip()
    )
    if fuzzy is None:
        fuzzy = _links_fuzzy_enabled(n_norm, n_lex)
    if not fuzzy and n_norm * n_lex > 25_000_000:
        print(
            f"build_links: fuzzy matching disabled (n_norm≈{n_norm} n_lex={n_lex}); "
            "exact / variant map only. Set HESPERIA_CALIB_LINKS_FUZZY=1 to force slow fuzzy.",
            flush=True,
        )

    links: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for r in normalized_rows:
        norm = str(r.get("normalized") or r.get("text", "")).strip()
        if not norm:
            continue
        variants = [norm] + [str(v).strip() for v in (r.get("variants") or []) if str(v).strip()]

        best_cid: str | None = None
        best_type = "unmapped"
        best_pr = 0.0

        for cand in variants:
            if cand in lexical_to_concept:
                cid, mt, pr = lexical_to_concept[cand]
                if pr > best_pr:
                    best_cid, best_type, best_pr = cid, mt, pr
            elif fuzzy:
                for lx, (cid, _, _) in lexical_to_concept.items():
                    s = _sim(cand, lx)
                    if s >= 0.88 and s > best_pr:
                        best_cid, best_type, best_pr = cid, "fuzzy", s

        if not best_cid and fuzzy:
            for lx, (cid, _, _) in lexical_to_concept.items():
                s = _sim(norm, lx)
                if s >= 0.82 and s > best_pr:
                    best_cid, best_type, best_pr = cid, "fuzzy", s

        if best_cid:
            key = (norm, best_cid)
            if key in seen:
                continue
            seen.add(key)
            links.append(
                {
                    "lexical": norm,
                    "concept_id": best_cid,
                    "match_type": best_type,
                    "priority": round(float(best_pr), 4),
                }
            )

    return links


def links_to_engine_dict_a(
    links: list[dict[str, Any]],
    *,
    version: str = "v0.6.0-cal",
    id_prefix: str = "CAL",
) -> list[dict[str, Any]]:
    """Emit DLCR matcher rows (``normalized_form``, ``candidate_concept_ids``, ...)."""
    rows: list[dict[str, Any]] = []
    for i, ln in enumerate(links, start=1):
        cid = str(ln.get("concept_id", ""))
        lex = str(ln.get("lexical", "")).strip()
        if not cid or not lex:
            continue
        mt = str(ln.get("match_type", "phrase"))
        map_type = "phrase" if mt != "exact" else "exact"
        pr = int(round(float(ln.get("priority", 0.8)) * 10))
        pr = max(1, min(10, pr))
        rows.append(
            {
                "entry_id": f"{id_prefix}-{i:05d}",
                "surface_form": lex,
                "normalized_form": lex,
                "match_type": map_type,
                "candidate_concept_ids": [cid],
                "priority": pr,
                "version": version,
            }
        )
    return rows
