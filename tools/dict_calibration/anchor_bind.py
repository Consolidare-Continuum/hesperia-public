# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.
"""Task 4 — Deterministic anchoring: bind draft concepts to Hesperia dict_b + hex (truth layer)."""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Literal

from core.hexmap.topology import load_hex_index_map

from . import repo_root

# Populated by multiprocessing pool initializer (fork workers).
_POOL_CONCEPT_INDEX: dict[str, dict[str, Any]] | None = None
_POOL_REG: dict[str, str] | None = None
_POOL_MIN: float = 0.52
_POOL_HX_MAP: dict[str, Any] | None = None


def _similarity(a: str, b: str) -> float:
    a, b = a.casefold().strip(), b.casefold().strip()
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _best_existing_concept(
    draft: dict[str, Any],
    concept_index: dict[str, dict[str, Any]],
    *,
    min_score: float = 0.52,
) -> tuple[str | None, float, str]:
    """Return (existing_concept_id, score, reason)."""
    did = str(draft.get("concept_id", "")).strip()
    if did in concept_index:
        return did, 1.0, "exact_id"

    labels = [str(x) for x in (draft.get("labels") or [])]
    lex = [str(x) for x in (draft.get("from_lexical") or [])]
    needles = [x for x in labels + lex if x]

    best_id: str | None = None
    best = 0.0
    for cid, row in concept_index.items():
        plab = str(row.get("preferred_label") or "")
        defin = str(row.get("definition") or "")[:240]
        for n in needles:
            s1 = _similarity(n, plab)
            s2 = max((_similarity(n, defin[j : j + 60]) for j in range(0, max(1, len(defin) - 40), 20)), default=0.0)
            s = max(s1, s2 * 0.85)
            if s > best:
                best = s
                best_id = cid

    if best_id and best >= min_score:
        return best_id, best, "fuzzy_label"
    return None, best, "no_match"


def _default_hex_map_path() -> Path:
    return repo_root() / "assets/data/engine_dynamics_v060/anchors/hex_index_map.json"


def _anchor_one_draft(
    d: dict[str, Any],
    concept_index: dict[str, dict[str, Any]],
    anchor_registry: dict[str, str],
    hx_map: dict[str, Any],
    *,
    min_score: float,
) -> tuple[Literal["anchored", "rejected"], dict[str, Any]]:
    eid, score, why = _best_existing_concept(d, concept_index, min_score=min_score)
    if not eid:
        return (
            "rejected",
            {
                "draft": d,
                "reason": "cannot_anchor",
                "best_score": round(score, 4),
                "detail": why,
            },
        )
    base = dict(concept_index[eid])
    sym = anchor_registry.get(eid) or base.get("hex_anchor")
    cell = int(hx_map[str(sym)]) if sym and str(sym) in hx_map else None
    row = {
        **base,
        "concept_id": eid,
        "calibration_bind_score": round(score, 4),
        "calibration_bind_reason": why,
        "calibration_draft_id": d.get("concept_id"),
        "calibration_from_lexical": list(d.get("from_lexical") or []),
        "family_id": (base.get("family_ids") or [""])[0],
        "area_id": (base.get("area_ids") or [""])[0],
        "hex_symbol": sym,
        "hex_id": cell,
    }
    return "anchored", row


def _anchor_pool_initializer(
    db_path_strs: tuple[str, ...],
    anch_path_str: str,
    min_score: float,
    hex_path_str: str,
) -> None:
    global _POOL_CONCEPT_INDEX, _POOL_REG, _POOL_MIN, _POOL_HX_MAP
    paths = [Path(p) for p in db_path_strs]
    merged = load_merged_dict_b(paths)
    _POOL_CONCEPT_INDEX = {str(r["concept_id"]): r for r in merged}
    _POOL_REG = load_anchor_registry(Path(anch_path_str))
    _POOL_MIN = float(min_score)
    hp = Path(hex_path_str)
    _POOL_HX_MAP = load_hex_index_map(hp) if hp.is_file() else {}


def _anchor_pool_worker(idx_draft: tuple[int, dict[str, Any]]) -> tuple[int, str, dict[str, Any]]:
    assert _POOL_CONCEPT_INDEX is not None
    assert _POOL_REG is not None
    assert _POOL_HX_MAP is not None
    idx, d = idx_draft
    kind, payload = _anchor_one_draft(
        d,
        _POOL_CONCEPT_INDEX,
        _POOL_REG,
        _POOL_HX_MAP,
        min_score=_POOL_MIN,
    )
    return idx, kind, payload


def anchor_drafts(
    drafts: list[dict[str, Any]],
    concept_index: dict[str, dict[str, Any]],
    anchor_registry: dict[str, str],
    *,
    hex_map_path: Path | None = None,
    min_score: float = 0.52,
    workers: int = 1,
    dict_b_paths: list[Path] | None = None,
    anchor_registry_path: Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Bind each draft to an existing Hesperia concept row when similarity passes.

    Output rows extend dict_b-shaped metadata plus ``hex_id`` (cell index) and ``hex_symbol``.

    When ``workers > 1``, uses a process pool (good for very large ``drafts``). Requires
    ``dict_b_paths`` and ``anchor_registry_path`` so workers can load the same truth layer.
    """
    hpath = hex_map_path or _default_hex_map_path()
    hx_map = load_hex_index_map(hpath) if hpath.exists() else {}

    if workers <= 1:
        anchored: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for d in drafts:
            kind, payload = _anchor_one_draft(
                d, concept_index, anchor_registry, hx_map, min_score=min_score
            )
            if kind == "rejected":
                rejected.append(payload)
            else:
                anchored.append(payload)
        return anchored, rejected

    if not dict_b_paths or anchor_registry_path is None:
        raise ValueError("anchor_drafts(workers>1) requires dict_b_paths and anchor_registry_path")
    db_strs = tuple(str(p.resolve()) for p in dict_b_paths if p.exists())
    if not db_strs:
        raise ValueError("anchor_drafts(workers>1): no existing dict_b_paths")
    hex_str = str(hpath.resolve()) if hpath.exists() else str(_default_hex_map_path().resolve())
    anch_str = str(anchor_registry_path.resolve())

    n = len(drafts)
    chunksize = max(32, min(512, n // (workers * 16) or 32))
    indexed = list(enumerate(drafts))
    with Pool(
        workers,
        initializer=_anchor_pool_initializer,
        initargs=(db_strs, anch_str, min_score, hex_str),
    ) as pool:
        raw = pool.map(_anchor_pool_worker, indexed, chunksize=chunksize)

    raw.sort(key=lambda t: t[0])
    anchored = []
    rejected = []
    for _i, kind, payload in raw:
        if kind == "rejected":
            rejected.append(payload)
        else:
            anchored.append(payload)
    return anchored, rejected


def load_merged_dict_b(paths: list[Path]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for p in paths:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            cid = row.get("concept_id")
            if cid and str(cid) not in by_id:
                by_id[str(cid)] = row
    return [by_id[k] for k in sorted(by_id)]


def load_anchor_registry(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}
