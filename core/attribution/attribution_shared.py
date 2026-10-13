# HESPERIA — Reference Architecture Definition (RAD)
# Copyright © 2026 Societatea cu Răspundere Limitată "CONSOLIDARE CONTINUUM" (IDNO 1026023120076). All rights reserved.
# Restricted Research Disclosure License. Inspection and reference only.
# No reproduction, redistribution, or use without explicit written permission from CONSOLIDARE CONTINUUM S.R.L.
# See LEGAL_NOTICE.md for full terms.

"""
HESPERIA v0.3.3 — deterministic attribution and region seeding.
Step 0: normalize (NFKC, lowercase, whitespace collapse, cap).
Step 1: tokenize (whitespace split, strip punctuation).
Step 2: attribution (Dict A exact → familyGlobal + altitude; Dict B fallback).
Aggregation: dominant family = argmax hits; tie-break lowest meanAltitude then lowest familyGlobal.
Region seed: tau(side) = base_weight * hitDensity_F * (1 - meanAltitude_F) for sides in F.
No stochastic learning. Dictionary-based only.

Tokenization: No heuristic regex rules; only deterministic punctuation stripping via a fixed
ASCII punctuation character set (implementation uses re for that fixed set only).
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

try:
    from lexicon.build.definitions.v0414.explain_landing import explain_landing
except ImportError:
    def explain_landing(
        token: str,
        dict_a: dict[str, dict[str, Any]],
        b0: dict[str, int],
        b1_optional: dict[str, int] | None,
    ) -> dict[str, Any]:
        t = token.strip().lower()
        if t in dict_a:
            return {"landing_source": "A", "familyGlobal": int(dict_a[t].get("familyGlobal", -1))}
        if t in b0:
            return {"landing_source": "B0", "familyGlobal": int(b0[t])}
        return {"landing_source": "NONE", "familyGlobal": None}

try:
    from core.topology.invariant_catalog import (
        FAMILIES_PER_AREA,
        SIDES_PER_FAMILY,
        TOTAL_SIDES,
        forward,
        validate_side_id,
    )
except ImportError:
    from invariant_catalog import (
        FAMILIES_PER_AREA,
        SIDES_PER_FAMILY,
        TOTAL_SIDES,
        forward,
        validate_side_id,
    )

# Default cap (configurable)
DEFAULT_TEXT_CAP = 10_000

# Punctuation strip: fixed ASCII set only. No heuristic patterns.
_PUNCT = re.escape(r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""")
_STRIP_PUNCT_RE = re.compile(f"[{_PUNCT}]")

# Legacy Dict A coefficient semantics (locked): coefficient = strength (higher = stronger anchor).
# altitude = 1 - clamp(coefficient). So high coefficient → low altitude (strong anchor).
LEGACY_WEIGHT_IS_STRENGTH = True


def normalize(text: str, cap: int = DEFAULT_TEXT_CAP) -> str:
    """
    Step 0: NFKC, lowercase, deterministic whitespace collapse, hard cap.
    """
    if not isinstance(text, str):
        text = str(text)
    s = unicodedata.normalize("NFKC", text).lower().strip()
    s = " ".join(s.split())
    if len(s) > cap:
        s = s[:cap]
    return s


def tokenize_with_spans(normalized: str) -> tuple[list[str], list[tuple[int, int]]]:
    """
    Same tokens as ``tokenize(normalized)``, plus ``[start, end)`` character spans in ``normalized``.

    Spans align with ``tokenize`` (punctuation stripped from each whitespace-delimited word). Using
    ``find(token)`` on the full string is wrong when the token is not a contiguous substring (e.g.
    ``02.38`` → ``0238``), which broke R1 sentence partitioning on Russian clinical transcripts.
    """
    tokens: list[str] = []
    spans: list[tuple[int, int]] = []
    scan = 0
    for w in normalized.split():
        idx = normalized.find(w, scan)
        if idx < 0:
            idx = scan
        scan = idx + len(w)
        core = _STRIP_PUNCT_RE.sub("", w).strip()
        if not core:
            continue
        kept = [i for i, ch in enumerate(w) if _STRIP_PUNCT_RE.sub("", ch)]
        if not kept:
            continue
        ts = idx + kept[0]
        te = idx + kept[-1] + 1
        tokens.append(core)
        spans.append((ts, te))
    return tokens, spans


def tokenize(normalized: str) -> list[str]:
    """
    Step 1: Whitespace split, strip punctuation. No stemming. Deterministic.
    """
    toks, _ = tokenize_with_spans(normalized)
    return toks


def _clamp_altitude(a: float) -> float:
    return max(0.0, min(1.0, float(a)))


def load_dict_a_v06(assets_root: Path) -> dict[str, dict[str, Any]]:
    """
    Load Dict A from v06 JSONL (token -> topk). Convert to v033 shape: lemma -> { familyGlobal, altitude }.
    Uses first topk entry: familyGlobal = family_id, altitude = 1 - w (strength semantics).
    Returns dict suitable for attribute(); empty if file missing.
    """
    v06_dir = Path(assets_root) / "v0_5_0"
    path = v06_dir / "dict_a_v06.jsonl"
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            token = (rec.get("token") or "").strip().lower()
            if not token:
                continue
            topk = rec.get("topk") or []
            if not topk:
                continue
            first = topk[0]
            fg = int(first.get("family_id", 0))
            w = float(first.get("w", 0.5))
            if 0 <= fg < 288:
                alt = _clamp_altitude(1.0 - w) if LEGACY_WEIGHT_IS_STRENGTH else _clamp_altitude(w)
                out[token] = {"familyGlobal": fg, "altitude": alt}
    return out


def load_dict_a_v033(path: Path | None = None, assets_root: Path | None = None) -> dict[str, dict[str, Any]]:
    """
    Load Dict A for v0.3.3 attribution.
    Native format: lemma -> { "familyGlobal": int, "altitude": float } (one family per lemma).
    Legacy format: lemma -> list of { "side_id": int, "coefficient": float }.
      - First entry only is used (deterministic). Multi-side across families: first entry wins.
      - familyGlobal = side_id // SIDES_PER_FAMILY.
      - Legacy weight semantics (locked): weight = strength (higher = stronger). altitude = 1 - clamp(weight).
    Returns dict: lemma -> { "familyGlobal": int, "altitude": float }.
    """
    root = assets_root or Path(__file__).resolve().parents[2] / "assets" / "lexicon" / "curated"
    # Default: last frozen A (v0.4.1.3 filename lineage — LEGACY asset label; bundle path v0_5_0).
    default = root / "A_CORE_STAR_MAP_v0_4_1_3.json"
    path = path or default
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out: dict[str, dict[str, Any]] = {}
    for k, v in data.items():
        if k.startswith("_") or v is None:
            continue
        if isinstance(v, dict) and "familyGlobal" in v:
            fg = int(v["familyGlobal"])
            alt = _clamp_altitude(v.get("altitude", 0.5))
            if 0 <= fg < 288:
                out[k.strip().lower()] = {"familyGlobal": fg, "altitude": alt}
        elif isinstance(v, list) and len(v) > 0:
            e = v[0]
            if isinstance(e, dict):
                sid = e.get("side_id")
                w = e.get("weight", 0.5)
                if sid is not None:
                    try:
                        sid_int = int(sid)
                        if 0 <= sid_int < TOTAL_SIDES:
                            fg = sid_int // SIDES_PER_FAMILY
                            w_clamped = _clamp_altitude(w)
                            alt = (1.0 - w_clamped) if LEGACY_WEIGHT_IS_STRENGTH else w_clamped
                            out[k.strip().lower()] = {"familyGlobal": fg, "altitude": alt}
                    except (TypeError, ValueError):
                        pass
    return out


def load_dict_a_surface_map_v033(assets_root: Path | None = None) -> dict[str, str]:
    """
    Load surface map: user-facing token -> structural key (e.g. "altruism" -> "altruism_1_10").
    At runtime, normalized token is resolved via this map before Dict A lookup; no structural IDs exposed to users.
    Returns dict: surface_lower -> structural_key. Empty if file missing.
    """
    root = assets_root or Path(__file__).resolve().parents[2] / "assets" / "lexicon" / "curated"
    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "DICT_A_SURFACE_MAP_v0_4_1_3.json",
        repo_root / "assets" / "lexicon" / "curated" / "DICT_A_SURFACE_MAP_v0_4_1_3.json",
        repo_root / "assets" / "lexicon" / "frozen" / "DICT_A_SURFACE_MAP_v0_4_1_3.json",
    ]
    for path in candidates:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {str(k).strip().lower(): str(v) for k, v in data.items() if isinstance(v, str)}
    return {}


def load_dict_b_v033(path: Path | None = None, assets_root: Path | None = None) -> dict[str, int]:
    """
    Load Dict B for v0.3.3: token -> familyGlobal.
    Legacy B: side_id (str) -> { canonical_lemma, aliases } -> build inverse: lemma/alias -> side_id -> familyGlobal.
    Returns dict: token_lower -> familyGlobal (0..287).
    """
    root = assets_root or Path(__file__).resolve().parents[2] / "assets" / "lexicon" / "curated"
    repo_root = Path(__file__).resolve().parents[2]
    b0_name = "B0_TOKEN_TO_FAMILY_v0_4_1_4_from_A_v0_4_1_3.json"
    b1_name = "B1_SIDE_TO_FAMILY_v0_4_1_4.json"
    # When assets_root is provided (e.g. lexicon/curated), try frozen alongside it so run sees Dict B after surface.
    b0_candidates: list[Path] = []
    b1_candidates: list[Path] = []
    if assets_root:
        ax = Path(assets_root)
        b0_candidates.append(ax.parent / "frozen" / b0_name)
        b1_candidates.append(ax.parent / "frozen" / b1_name)
    b0_candidates.append(repo_root / "assets" / "lexicon" / "frozen" / b0_name)
    b1_candidates.append(repo_root / "assets" / "lexicon" / "frozen" / b1_name)
    token_to_side_path = root / "token_to_side_id_v040.json"
    legacy_path = path or (root / "B0_TOKEN_TO_FAMILY_v0_4_1_4_from_A_v0_4_1_3.json")

    b0: dict[str, int] = {}
    for candidate in b0_candidates:
        if candidate.exists():
            with open(candidate, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                b0 = {str(k).strip().lower(): int(v) for k, v in data.items() if isinstance(k, str)}
                break

    b1: dict[str, int] = {}
    for candidate in b1_candidates:
        if candidate.exists():
            with open(candidate, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                b1 = {str(k): int(v) for k, v in data.items() if isinstance(k, str)}
                break

    token_to_side: dict[str, int] = {}
    if token_to_side_path.exists():
        with open(token_to_side_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            token_to_side = {str(k).strip().lower(): int(v) for k, v in data.items() if isinstance(k, str)}

    legacy: dict[str, int] = {}
    if legacy_path.exists():
        with open(legacy_path, encoding="utf-8") as f:
            data = json.load(f)
        for sid_str, entry in data.items():
            if not isinstance(entry, dict):
                continue
            try:
                sid_int = int(sid_str)
            except (TypeError, ValueError):
                continue
            if sid_int < 0 or sid_int >= TOTAL_SIDES:
                continue
            fg = sid_int // SIDES_PER_FAMILY
            lemma = entry.get("canonical_lemma") or entry.get("lemma")
            if isinstance(lemma, str) and lemma.strip():
                legacy[lemma.strip().lower()] = fg
            for alias in entry.get("aliases") or []:
                if isinstance(alias, str) and alias.strip():
                    legacy[alias.strip().lower()] = fg

    # Token landing fallback map used by existing callers:
    # B1 token->side->family when mapping exists; then B0; then legacy.
    out = dict(legacy)
    out.update(b0)
    if token_to_side and b1:
        for token, side_id in token_to_side.items():
            family = b1.get(str(side_id))
            if family is not None:
                out[token] = family
    return out


def attribute(
    tokens: list[str],
    dict_a: dict[str, dict[str, Any]],
    dict_b: dict[str, int],
    default_altitude_b: float = 0.5,
    surface_map: dict[str, str] | None = None,
) -> tuple[list[tuple[int, float]], dict[str, Any]]:
    """
    For each token: resolve surface -> structural key via surface_map (if provided); Dict A exact match -> (familyGlobal, altitude); else Dict B -> (familyGlobal, default_altitude_b); else ignore.
    Returns (list of (familyGlobal, altitude) for matched tokens), extended_metrics dict.
    """
    default_altitude_b = _clamp_altitude(default_altitude_b)
    matched: list[tuple[int, float]] = []
    total = len(tokens)
    landing_counts = {"A": 0, "B0": 0, "B1": 0, "NONE": 0}
    for t in tokens:
        key = (surface_map.get(t, t) if surface_map else t)
        # For v0.3.3 compatibility, dict_b is already a merged deterministic fallback map.
        # explain_landing is used as a minimal logging helper (A/B0/NONE here; B1 when token->side map is provided).
        explained = explain_landing(key, dict_a=dict_a, b0=dict_b, b1_optional=None)
        source = explained["landing_source"]
        if source == "A":
            fg = int(explained["familyGlobal"])
            alt = _clamp_altitude(dict_a[key].get("altitude", 0.5))
            if 0 <= fg < 288:
                matched.append((fg, alt))
                landing_counts[source] += 1
            else:
                landing_counts["NONE"] += 1
        elif source in ("B0", "B1"):
            fg = int(explained["familyGlobal"])
            if 0 <= fg < 288:
                matched.append((fg, default_altitude_b))
                landing_counts[source] += 1
            else:
                landing_counts["NONE"] += 1
        else:
            landing_counts["NONE"] += 1
    unmatched = total - len(matched)
    coverage = (len(matched) / total) if total > 0 else 0.0
    mean_alt_global = (sum(m[1] for m in matched) / len(matched)) if matched else 0.0
    metrics = {
        "total_tokens": total,
        "matched_tokens": len(matched),
        "unmatched_tokens": unmatched,
        "attribution_coverage": coverage,
        "meanAltitude_global": mean_alt_global,
        "landing_source_counts": landing_counts,
    }
    return matched, metrics


def aggregate_dominant(matched: list[tuple[int, float]]) -> tuple[int, int, float, float, dict[str, Any]]:
    """
    Per-family: count hits, meanAltitude_F, hitDensity_F = hits_F / total_hits.
    Dominant family = argmax(hits_F). Tie-break: lowest meanAltitude wins, then lowest familyGlobal.
    Dominant area = floor(dominant_family / 24).
    Returns (dominant_family, dominant_area, meanAltitude_F, hitDensity_F, per_family_stats).
    """
    if not matched:
        return 0, 0, 0.0, 0.0, {}
    total_hits = len(matched)
    by_family: dict[int, list[float]] = {}
    for fg, alt in matched:
        by_family.setdefault(fg, []).append(alt)
    # Dominant = argmax hits; tie-break: lowest meanAltitude, then lowest familyGlobal
    candidates = [(fg, len(alts), sum(alts) / len(alts)) for fg, alts in by_family.items()]
    candidates.sort(key=lambda x: (-x[1], x[2], x[0]))
    best_fg = candidates[0][0] if candidates else 0
    dominant_area = best_fg // FAMILIES_PER_AREA
    mean_alt_f = sum(by_family[best_fg]) / len(by_family[best_fg])
    hit_density_f = len(by_family[best_fg]) / total_hits
    per_family = {str(fg): {"hits": len(alts), "meanAltitude": sum(alts) / len(alts), "hitDensity": len(alts) / total_hits} for fg, alts in by_family.items()}
    return best_fg, dominant_area, mean_alt_f, hit_density_f, per_family


def build_region_seed(
    dominant_family: int,
    hit_density_f: float,
    mean_altitude_f: float,
    base_weight: float = 1.0,
) -> list[tuple[int, float]]:
    """
    Seed S = all sides in family F (250 hexes × 6 sides = 1500).
    tau(side) = base_weight * hitDensity_F * (1 - meanAltitude_F). All tau >= 0, finite.
    Returns list of (sideId, tau).
    """
    if not (0 <= dominant_family < 288):
        return []
    tau_val = base_weight * hit_density_f * (1.0 - mean_altitude_f)
    tau_val = max(0.0, min(1.0, tau_val))
    if not math.isfinite(tau_val):
        tau_val = 0.0
    seed: list[tuple[int, float]] = []
    for hex_local in range(250):
        for side_local in range(6):
            area = dominant_family // FAMILIES_PER_AREA
            family_local = dominant_family % FAMILIES_PER_AREA
            side_id = forward(area, family_local, hex_local, side_local)
            validate_side_id(side_id)
            seed.append((side_id, tau_val))
    return seed


def run_attribution_pipeline(
    text: str,
    cap: int = DEFAULT_TEXT_CAP,
    dict_a_path: Path | None = None,
    dict_b_path: Path | None = None,
    assets_root: Path | None = None,
    mode: str | None = None,
) -> tuple[int, int, list[tuple[int, float]], dict[str, Any], dict[str, Any]]:
    """
    Full Steps 0–2: normalize -> tokenize -> attribute -> aggregate -> seed.
    Returns (dominant_family, dominant_area, seed list (sideId, tau), attribution_metrics, extended_metrics).
    Raises on semantic vacuum (no tokens or no matches) — caller returns 400.
    """
    normalized = normalize(text, cap=cap)
    tokens = tokenize(normalized)
    if not tokens:
        raise ValueError("semantic_vacuum: no tokens after tokenize")
    dict_a = load_dict_a_v033(path=dict_a_path, assets_root=assets_root)
    dict_b = load_dict_b_v033(path=dict_b_path, assets_root=assets_root)
    surface_map = load_dict_a_surface_map_v033(assets_root=assets_root)
    matched, attr_metrics = attribute(tokens, dict_a, dict_b, surface_map=surface_map if surface_map else None)
    if not matched:
        raise ValueError("semantic_vacuum: no tokens matched any dictionary")
    dominant_family, dominant_area, mean_alt_f, hit_density_f, per_family = aggregate_dominant(matched)
    seed = build_region_seed(dominant_family, hit_density_f, mean_alt_f)
    extended = {**attr_metrics, "per_family": per_family}
    return dominant_family, dominant_area, seed, attr_metrics, extended
