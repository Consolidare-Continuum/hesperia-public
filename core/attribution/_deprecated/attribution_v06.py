# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.6 — Runtime attribution from Dict A (full 288-family field).
Loads dict_a_v06.jsonl + family_prior_v06.json. Token → 288 weights; sentence = mean; dominant = argmax.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .attribution_shared import DEFAULT_TEXT_CAP, normalize, tokenize
from core.topology.invariant_catalog import (
    FAMILIES_PER_AREA,
    HEXES_PER_FAMILY,
    SIDES_PER_HEX,
    TOTAL_FAMILIES,
    forward,
    validate_side_id,
)

TOP_K = 32
EPS = 1e-9

_REPO = Path(__file__).resolve().parents[2]
# Canonical frozen bundle id (v0.5.0): physical dir v0_5_0 → symlink to legacy v06 payload layout.
_DEFAULT_LEXICON_FROZEN_BUNDLE = _REPO / "assets" / "lexicon" / "frozen" / "v0_5_0"
_dict_a: dict[str, dict[str, Any]] | None = None
_family_prior: list[float] | None = None
_surface_map: dict[str, str] | None = None


def load_dict_a(
    dict_a_path: Path | None = None,
    prior_path: Path | None = None,
    v06_dir: Path | None = None,
    assets_root: Path | None = None,
) -> tuple[dict[str, dict[str, Any]], list[float]]:
    """Load dict_a_v06.jsonl and family_prior_v06.json. Optionally load surface map."""
    global _dict_a, _family_prior, _surface_map
    base = v06_dir or _DEFAULT_LEXICON_FROZEN_BUNDLE
    dict_path = dict_a_path or base / "dict_a_v06.jsonl"
    prior_file = prior_path or base / "family_prior_v06.json"
    if not dict_path.exists():
        raise FileNotFoundError(f"Dict A artifact not found: {dict_path}. Run build_dict_a.py first.")
    if not prior_file.exists():
        raise FileNotFoundError(f"Family prior not found: {prior_file}")
    out: dict[str, dict[str, Any]] = {}
    with open(dict_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            token = rec.get("token", "").strip().lower()
            if token:
                out[token] = rec
    with open(prior_file, encoding="utf-8") as f:
        data = json.load(f)
    prior = data.get("family_prior", [])
    if len(prior) != TOTAL_FAMILIES:
        raise ValueError(f"family_prior must have {TOTAL_FAMILIES} entries, got {len(prior)}")
    try:
        from .attribution_shared import load_dict_a_surface_map_v033
        _surface_map = load_dict_a_surface_map_v033(assets_root=assets_root or _REPO / "assets" / "lexicon" / "frozen")
    except Exception:
        _surface_map = {}
    _dict_a = out
    _family_prior = prior
    return out, prior


def _get_weights_for_token(token: str) -> list[float]:
    global _dict_a, _family_prior, _surface_map
    if _dict_a is None or _family_prior is None:
        load_dict_a()
    prior = _family_prior
    t = token.strip().lower()
    key = (_surface_map or {}).get(t, t)
    if key not in _dict_a:
        return list(prior)
    entry = _dict_a[key]
    topk = entry.get("topk", [])
    weights = [0.0] * TOTAL_FAMILIES
    topk_sum = 0.0
    for item in topk:
        fid = int(item.get("family_id", 0))
        w = float(item.get("w", 0))
        if 0 <= fid < TOTAL_FAMILIES:
            weights[fid] = w
            topk_sum += w
    tail_mass = 1.0 - topk_sum
    if tail_mass <= 0 or tail_mass < 1e-10:
        return weights
    topk_ids = {int(item.get("family_id", 0)) for item in topk if 0 <= int(item.get("family_id", 0)) < TOTAL_FAMILIES}
    sum_prior_excl = sum(prior[f] for f in range(TOTAL_FAMILIES) if f not in topk_ids)
    if sum_prior_excl <= 0:
        return weights
    for f in range(TOTAL_FAMILIES):
        if f not in topk_ids:
            weights[f] = tail_mass * (prior[f] / sum_prior_excl)
    return weights


def _sentence_vector(tokens: list[str]) -> list[float]:
    if not tokens:
        return [0.0] * TOTAL_FAMILIES
    n = len(tokens)
    acc = [0.0] * TOTAL_FAMILIES
    for t in tokens:
        w = _get_weights_for_token(t)
        for f in range(TOTAL_FAMILIES):
            acc[f] += w[f]
    vec = [acc[f] / n for f in range(TOTAL_FAMILIES)]
    total = sum(vec) or 1.0
    return [vec[f] / total for f in range(TOTAL_FAMILIES)]


def _dominant_from_vector(sentence_vector: list[float]) -> tuple[int, int]:
    best_f = 0
    best_w = sentence_vector[0]
    for f in range(1, TOTAL_FAMILIES):
        if sentence_vector[f] > best_w:
            best_w = sentence_vector[f]
            best_f = f
    return best_f, best_f // FAMILIES_PER_AREA


def _build_seed_weighted(sentence_vector: list[float], eps: float = EPS) -> list[tuple[int, float]]:
    masses = [(f, sentence_vector[f]) for f in range(TOTAL_FAMILIES) if sentence_vector[f] > eps]
    if not masses:
        return []
    total = sum(m for _, m in masses)
    if total <= 0:
        return []
    seed: list[tuple[int, float]] = []
    for f, m in masses:
        tau = max(0.0, min(1.0, m / total))
        if not math.isfinite(tau):
            tau = 0.0
        family_local = f % FAMILIES_PER_AREA
        area = f // FAMILIES_PER_AREA
        for hex_local in range(HEXES_PER_FAMILY):
            for side_local in range(SIDES_PER_HEX):
                side_id = forward(area, family_local, hex_local, side_local)
                validate_side_id(side_id)
                seed.append((side_id, tau))
    return seed


def run_attribution_pipeline(
    text: str,
    cap: int = DEFAULT_TEXT_CAP,
    assets_root: Path | None = None,
    v06_dir: Path | None = None,
) -> tuple[int, int, list[tuple[int, float]], dict[str, Any], dict[str, Any]]:
    """v0.6: normalize → tokenize → 288 weights → sentence = mean → dominant = argmax, weighted seed."""
    normalized = normalize(text, cap=cap)
    tokens = tokenize(normalized)
    if not tokens:
        raise ValueError("semantic_vacuum: no tokens after tokenize")
    base = v06_dir or (assets_root and assets_root / "v0_5_0") or _DEFAULT_LEXICON_FROZEN_BUNDLE
    if _dict_a is None or _family_prior is None:
        load_dict_a(
            v06_dir=base,
            assets_root=assets_root or (_REPO / "assets" / "lexicon" / "frozen"),
        )
    sentence_vector = _sentence_vector(tokens)
    dominant_family, dominant_area = _dominant_from_vector(sentence_vector)
    seed = _build_seed_weighted(sentence_vector, eps=EPS)
    n = len(tokens)
    mean_alt = sum(sentence_vector) / TOTAL_FAMILIES if sentence_vector else 0.0
    attr_metrics = {
        "total_tokens": n,
        "matched_tokens": n,
        "unmatched_tokens": 0,
        "attribution_coverage": 1.0,
        "meanAltitude_global": mean_alt,
        "mode": "v06",
    }
    extended = {
        **attr_metrics,
        "family_vector": sentence_vector,
        "family_vector_pre_sharpen": sentence_vector,
    }
    return dominant_family, dominant_area, seed, attr_metrics, extended
