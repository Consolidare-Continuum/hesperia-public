# HESPERIA — RAD. DLCR L0→L6 single entry for integration (Ethan INT-010).
# Copyright © 2026 igareosh.com. See LEGAL_NOTICE.md.

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from core.diagnostics.failures import classify_failures
from core.dynamics.constants import get_constant
from core.dynamics.numeric import EPS, quantize
from core.hexmap.aggregate import aggregate_hex_state, cross_family_relation_sketch
from core.hexmap.analytics import l1_drift, persistence_score
from core.guards.determinism import guard_determinism
from core.guards.invariants import enforce_invariants
from core.hexmap.topology import load_hex_index_map
from core.lexical.cooccurrence import pair_counts_from_canonical
from core.lexical.policy import load_dlcr_policy
from core.output.result_builder import build_result
from core.pipeline.dynamics import (
    apply_decay,
    apply_decay_with_diagnostics,
    concentration_index,
    dispersion_index,
    smooth_toward_mean,
)
from core.lexical.matcher import _collect_negative_blocks
from core.pipeline.lexical import match_dict_a, normalize_text, prepare_structural_analysis_text
from core.pipeline.projection import project_concepts_to_hex
from core.pipeline.resolver import resolve_hit, resolve_paragraph_hits
from core.pipeline.trajectory import trajectory_over_segments
from core.resolver.context import paragraph_index_for_span, paragraph_spans
from core.resolver.dict_d_index import load_dict_d_pairs
from core.resolver.score_rules import effective_empirical_weight
from core.sequence.segmentation import segment_by_newlines
from core.state.semantic_state import SemanticState
from hesperia.engine.calibration_dict_paths import (
    calibration_manifest,
    resolve_dict_d_file,
    resolve_dict_file,
)
from hesperia.engine.concept_dictionary.executor import apply_cd_phase1, default_cd_path
from hesperia.engine.engine_signal_calibration import load_engine_signal_calibration
from hesperia.extensions.triz.topology_activation_pipeline import concept_id_to_area_family

_DEFAULT_STOPWORDS: frozenset[str] = frozenset(
    {"и", "в", "на", "с", "к", "по", "но", "а", "я", "он", "мы"}
)
_DEFAULT_DOMAIN_WHITELIST: frozenset[str] = frozenset(
    {
        "перенос",
        "контрперенос",
        "объект",
        "отнош",
        "аффект",
        "идент",
        "защит",
    }
)
_DEFAULT_COMPETING_GROUPS: tuple[tuple[str, ...], ...] = (
    ("TFP_TRANSFERENCE", "TFP_COUNTERTRANSFERENCE", "TFP_POLARIZATION"),
    ("TFP_REPRESENTATION_SELF", "TFP_REPRESENTATION_OBJECT"),
)


def _load_runtime_stopwords() -> frozenset[str]:
    raw = os.environ.get("HESPERIA_DLCR_STOPWORDS", "").strip()
    if not raw:
        return _DEFAULT_STOPWORDS
    return frozenset(x.strip().casefold() for x in raw.split(",") if x.strip())


def _load_domain_whitelist() -> frozenset[str]:
    raw = os.environ.get("HESPERIA_DLCR_DOMAIN_WHITELIST", "").strip()
    if not raw:
        return _DEFAULT_DOMAIN_WHITELIST
    return frozenset(x.strip().casefold() for x in raw.split(",") if x.strip())


def _drop_low_quality_token(
    token: str,
    *,
    stopwords: frozenset[str],
    min_len: int,
    domain_whitelist: frozenset[str],
) -> bool:
    t = token.strip()
    if not t:
        return True
    tc = t.casefold()
    # Domain whitelist bypasses structural filters.
    if any(key in tc for key in domain_whitelist):
        return False
    if len(t) < int(min_len):
        return True
    if tc in stopwords:
        return True
    # Optional tiny-fragment rejection (off by default to avoid over-filtering).
    if (
        os.environ.get("HESPERIA_DLCR_REJECT_TINY_FRAGMENTS", "").strip().lower()
        in {"1", "true", "yes"}
        and " " in t
        and len(t) < 4
    ):
        return True
    return False


def _classify_span_resolution(
    resolution: dict[str, Any],
    *,
    min_resolve_score: float,
) -> tuple[dict[str, Any], bool]:
    scores = resolution.get("candidate_scores")
    if not isinstance(scores, dict):
        raise ValueError("span resolution candidate_scores must be an object")
    if not scores:
        unresolved = dict(resolution)
        unresolved["winning_concept_id"] = None
        unresolved["winning_reason_codes"] = []
        unresolved["rejected_reason_codes"] = ["no_candidates"]
        return unresolved, False

    best_score = max(float(score) for score in scores.values())
    if best_score >= min_resolve_score:
        return resolution, True

    unresolved = dict(resolution)
    unresolved["winning_concept_id"] = None
    unresolved["winning_reason_codes"] = []
    unresolved["rejected_reason_codes"] = sorted(
        ["below_threshold"]
        + [f"candidate_rejected:{concept_id}" for concept_id in scores]
    )
    return unresolved, False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def _hit_family_diversity_key(hit: Any) -> str:
    """Family key (``A10_F10``) for the hit's primary candidate concept, used to
    round-robin ``dict_a_max_accepted`` across families instead of a flat position
    cut. Falls back to ``entry_id`` for ids that don't parse (still deterministic,
    just not family-grouped) so the cap never silently ignores hits it can't parse.
    """
    cids = hit.candidate_concept_ids
    if cids:
        parsed = concept_id_to_area_family(str(cids[0]))
        if parsed:
            return parsed[1]
    return f"_unparsed:{hit.entry_id}"


def _merge_dict_b(paths: list[Path]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for p in paths:
        for row in _load_jsonl(p):
            cid = row.get("concept_id")
            if cid and cid not in by_id:
                by_id[str(cid)] = row
    return [by_id[k] for k in sorted(by_id)]


def _merge_dict_a(paths: list[Path]) -> list[dict[str, Any]]:
    """
    Merge Dict A files in path order. Non-negative rows dedupe on ``normalized_form``
    (first file wins) so curated RU layers override legacy ``dict_a_tfp`` collisions.
    Negative-pattern rows always append (unique phrases).
    """
    rows: list[dict[str, Any]] = []
    seen_nf: set[str] = set()
    syn_by_concept: dict[str, int] = {}
    confidence_threshold = float(
        os.environ.get(
            "HESPERIA_DICT_A_CONFIDENCE_THRESHOLD",
            str(get_constant("dictionary.confidence_threshold", 0.35)),
        )
    )
    max_synonyms_per_concept = int(
        os.environ.get(
            "HESPERIA_DICT_A_MAX_SYNONYMS_PER_CONCEPT",
            str(get_constant("dictionary.max_synonyms_per_concept", 24)),
        )
    )
    for p in paths:
        for row in _load_jsonl(p):
            conf = row.get("confidence")
            if conf is not None and float(conf) < confidence_threshold:
                continue
            if row.get("negative_patterns"):
                rows.append(row)
                continue
            nf = row.get("normalized_form")
            if not nf:
                continue
            if nf in seen_nf:
                continue
            concept_id = str(row.get("concept_id") or "")
            if concept_id:
                count = syn_by_concept.get(concept_id, 0)
                if count >= max_synonyms_per_concept:
                    continue
                syn_by_concept[concept_id] = count + 1
            seen_nf.add(nf)
            rows.append(row)
    return rows


def _family_slot_index(area: str, family: str) -> int | None:
    if not area.startswith("A") or not family.startswith("F"):
        return None
    try:
        an = int(area[1:])
        fn = int(family[1:])
    except ValueError:
        return None
    if not (1 <= an <= 12 and 1 <= fn <= 24):
        return None
    return (an - 1) * 24 + (fn - 1)


def _concept_weights_from_resolutions(
    resolved: list[dict[str, Any]],
    *,
    top_k: int = 3,
    debug: bool = False,
    rarity_weighting: bool = True,
) -> dict[str, float]:
    """
    Bounded multi-candidate aggregation with per-token mass conservation.

    For each resolved token/span:
      1) take candidate_scores
      2) keep top-K
      3) normalize so per-token mass sums to 1
      4) add normalized mass to global concept weights
    """
    k = max(1, int(top_k or 1))
    weights: dict[str, float] = {}
    token_freq: Counter[str] = Counter()
    for r in resolved:
        token = str(r.get("source_text_span") or "").strip()
        if token:
            token_freq[token.casefold()] += 1

    for r in resolved:
        scores_raw = r.get("candidate_scores")
        cands: list[tuple[str, float]] = []
        if isinstance(scores_raw, dict):
            for cid, sv in scores_raw.items():
                s = float(sv or 0.0)
                if s > 0:
                    cands.append((str(cid), s))
        if not cands:
            # Back-compat fallback if scores are missing.
            winner = r.get("winning_concept_id")
            if winner:
                cands = [(str(winner), 1.0)]
            else:
                continue
        cands.sort(key=lambda t: (-t[1], t[0]))
        cands = cands[:k]
        total = sum(s for _cid, s in cands)
        if total <= 0:
            continue
        normalized = [(cid, s / total) for cid, s in cands]
        s_norm = sum(w for _cid, w in normalized)
        assert abs(s_norm - 1.0) < 1e-6, f"per-token mass conservation failed: {s_norm}"
        token = str(r.get("source_text_span") or "").strip()
        rw = 1.0
        if rarity_weighting and token:
            rw = 1.0 / (1.0 + float(token_freq[token.casefold()]))
        if debug:
            token = str(r.get("source_text_span") or "")
            print(f"[dlcr-token] {token[:80]!r} -> {normalized}")
        for cid, w in normalized:
            weights[cid] = weights.get(cid, 0.0) + float(w) * float(rw)

    # Competition inside known collapsed concept groups.
    for group in _DEFAULT_COMPETING_GROUPS:
        present = [cid for cid in group if cid in weights]
        if len(present) <= 1:
            continue
        tot = sum(weights[cid] for cid in present)
        if tot <= 0:
            continue
        for cid in present:
            weights[cid] = float(weights[cid]) / float(tot)

    # Damping to prevent runaway clusters.
    for cid in list(weights.keys()):
        weights[cid] = math.log1p(max(0.0, float(weights[cid])))
    return {k0: weights[k0] for k0 in sorted(weights)}


def _stabilize_concept_weights(
    raw_concepts: dict[str, float],
    *,
    token_count: int,
    concept_cap: float,
    log_normalization_enabled: bool,
) -> dict[str, float]:
    denom = math.sqrt(float(max(token_count, 1)))
    out: dict[str, float] = {}
    for cid, raw in raw_concepts.items():
        capped = min(max(0.0, float(raw)), float(concept_cap))
        value = math.log1p(capped) if log_normalization_enabled else capped
        out[cid] = quantize(value / denom)
    return {k: out[k] for k in sorted(out)}


def _post_hex_concept_feedback(
    concept_weights: dict[str, float],
    *,
    anchor_registry: dict[str, str],
    hex_decay: float,
    hex_smooth_alpha: float,
) -> tuple[SemanticState, SemanticState, dict[str, float], list[str], list[str]]:
    index_map: dict[str, int] | None = None
    try:
        # stable bounded locality map
        index_map = load_hex_index_map(_repo_root() / "assets" / "data" / "engine_dynamics_v060" / "anchors" / "hex_index_map.json")
    except Exception:
        index_map = None
    state_raw, degradation_flags = project_concepts_to_hex(
        concept_weights, anchor_registry, index_map=index_map, return_state=True
    )
    state_post, operator_diag = apply_decay_with_diagnostics(state_raw, decay=max(0.0, float(hex_decay)))
    if hex_smooth_alpha > 0:
        state_post = smooth_toward_mean(state_post, alpha=min(1.0, float(hex_smooth_alpha)))
    state_post, inv = enforce_invariants(state_post, clamp=True)
    post_hex: dict[str, float] = {}
    delta: dict[str, float] = {}
    for cid, weight in concept_weights.items():
        hex_id = anchor_registry.get(cid)
        if not hex_id:
            post_hex[cid] = float(weight)
            delta[cid] = 0.0
            continue
        raw_anchor = float(state_raw.mass_vector.get(hex_id) or 0.0)
        stable_anchor = float(state_post.mass_vector.get(hex_id) or 0.0)
        if raw_anchor <= 1e-12:
            scaled = float(weight)
        else:
            scaled = float(weight) * (stable_anchor / raw_anchor)
        post_hex[cid] = scaled
        delta[cid] = scaled - float(weight)
    post_hex = {k: quantize(v) for k, v in sorted(post_hex.items())}
    if not bool(operator_diag.get("energy_conservation_ok", True)):
        inv.append("forbidden_energy_loss")
    return state_raw, state_post, post_hex, sorted(degradation_flags), sorted(inv)


def _evolve_segment_state(
    state_prev: SemanticState,
    segment_concept_weights: dict[str, float],
    *,
    anchor_registry: dict[str, str],
    smooth_alpha: float,
) -> tuple[SemanticState, list[str]]:
    local_projection_state, _ = project_concepts_to_hex(
        segment_concept_weights,
        anchor_registry,
        return_state=True,
    )
    merged_mass = dict(state_prev.mass_vector)
    for key, value in local_projection_state.mass_vector.items():
        merged_mass[key] = merged_mass.get(key, 0.0) + float(value)
    state_next = SemanticState(
        energy_vector=dict(state_prev.energy_vector),
        activation_vector=dict(state_prev.activation_vector),
        mass_vector=merged_mass,
        position=dict(anchor_registry),
    )
    state_next = apply_decay(state_next, decay=float(get_constant("operator.decay_default", 0.05)))
    if smooth_alpha > EPS:
        state_next = smooth_toward_mean(state_next, alpha=min(1.0, smooth_alpha))
    state_next, invariants = enforce_invariants(state_next, clamp=True)
    return state_next, invariants


def _load_version_pins(repo: Path) -> dict[str, Any]:
    p = repo / "assets" / "data" / "engine_dynamics_v060" / "VERSION.yaml"
    if not p.exists():
        return {}
    try:
        import yaml  # type: ignore[import-untyped]

        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def compute_lexical_unmapped_token_rate(
    text: str,
    *,
    repo_root: Path | None = None,
    mode: str = "clinical_speech",
) -> float:
    """
    TFP-REL-01: fraction of whitespace-separated tokens in canonical text that do **not** overlap
    any **accepted** dict_a LexicalHit span (same merge + matcher as ``run_dlcr_pipeline``).
    """
    repo = repo_root or _repo_root()
    base = repo / "assets" / "data" / "engine_dynamics_v060"
    calib_a = resolve_dict_file(repo, "dict_a.jsonl")
    da_paths_default = [
        base / "dict_a" / "dict_a_seed.jsonl",
        base / "dict_a" / "dict_a_tfp.jsonl",
        base / "dict_a" / "dict_a_tfp_ru_core.jsonl",
        base / "dict_a" / "dict_a_tfp_ru_variants.jsonl",
        base / "dict_a" / "dict_a_tfp_ru_speech.jsonl",
        base / "dict_a" / "dict_a_tfp_ru_negative.jsonl",
        base / "dict_a" / "dict_a_tfp_ru_aligned.jsonl",
    ]
    da_paths = [calib_a] if calib_a else da_paths_default
    dict_a = _merge_dict_a(da_paths)
    pol = load_dlcr_policy(repo)
    raw_max = pol.get("dict_a_max_accepted")
    env_max = os.environ.get("HESPERIA_DICT_A_MAX_ACCEPTED", "").strip()
    if env_max.isdigit():
        max_acc: int | None = int(env_max)
    elif raw_max is not None and str(raw_max).strip().lstrip("-").isdigit():
        max_acc = int(raw_max)
    else:
        max_acc = None
    canonical, _prep_meta = prepare_structural_analysis_text(text, policy_mode=mode)
    norm = normalize_text(canonical)
    ct = norm["canonical_text"]
    hits, _rejected = match_dict_a(ct, dict_a, max_accepted=max_acc)
    tokens = list(re.finditer(r"\S+", ct))
    if not tokens:
        return 0.0
    unmapped = 0
    for m in tokens:
        ts, te = m.start(), m.end()
        covered = any(h.span_start < te and ts < h.span_end for h in hits)
        if not covered:
            unmapped += 1
    return unmapped / float(len(tokens))


def apply_crossplane_contradiction_fields_to_dlcr_result(
    result: dict[str, Any],
    contradiction_package: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge cross-plane contradiction metrics into an existing DLCR result (single-DLCR augment path)."""
    if not contradiction_package:
        return result
    pkg = contradiction_package
    g = float(pkg.get("global_contradiction_load") or 0.0)
    result["contradiction_load"] = round(max(0.0, min(1.0, g)), 6)
    result["cross_area_contradiction_mass"] = round(float(pkg.get("cross_area_contradiction_mass") or 0.0), 6)
    result["contradiction_stability_index"] = round(float(pkg.get("contradiction_stability_index") or 0.0), 6)
    result["contradiction_coherence_flag"] = bool(pkg.get("contradiction_coherence_flag"))
    result["contradiction_coupling_active"] = bool(pkg.get("contradiction_coupling_active"))
    conc = float(result.get("hex_concentration_index") or 0.0)
    disp = float(result.get("hex_dispersion_index") or 0.0)
    traj = result.get("trajectory") or {}
    result["dlcr_contradiction_alignment"] = _dlcr_contradiction_alignment_fields(
        conc,
        disp,
        traj if isinstance(traj, dict) else {},
        g,
    )
    fb = pkg.get("feedback_summary") if isinstance(pkg.get("feedback_summary"), dict) else {}
    tok = pkg.get("top_risky_tokens")
    if not isinstance(tok, list):
        tok = []
    ctop = pkg.get("top_risky_concepts")
    if not isinstance(ctop, list):
        ctop = []
    result["lexical_calibration_feedback"] = {
        "top_risky_tokens": list(tok[:20]),
        "mean_lexical_calibration_risk": round(
            sum(float(x.get("calibration_risk") or 0.0) for x in tok[:20]) / max(1, len(tok[:20])),
            6,
        ),
        "high_risk_token_share": round(float(fb.get("high_risk_token_share") or 0.0), 6),
    }
    result["concept_calibration_feedback"] = {
        "top_risky_concepts": list(ctop[:20]),
        "mean_concept_calibration_risk": round(
            sum(float(x.get("calibration_risk") or 0.0) for x in ctop[:20]) / max(1, len(ctop[:20])),
            6,
        ),
        "high_risk_concept_share": round(float(fb.get("high_risk_concept_share") or 0.0), 6),
    }
    return result


def _entropy01_from_concept_weights(cw: dict[str, float]) -> float:
    vals = [max(0.0, float(v)) for v in cw.values() if float(v) > EPS]
    if len(vals) < 2:
        return 0.0
    s = sum(vals)
    if s <= EPS:
        return 0.0
    ps = [v / s for v in vals]
    h = -sum(p * math.log(p + EPS) for p in ps)
    h_max = math.log(len(ps))
    return max(0.0, min(1.0, h / h_max)) if h_max > EPS else 0.0


def _ambiguous_span_ratio(span_outputs: list[dict[str, Any]]) -> float:
    if not span_outputs:
        return 0.0
    amb = 0
    for r in span_outputs:
        scores = r.get("candidate_scores") or {}
        if not isinstance(scores, dict) or len(scores) < 2:
            continue
        vals = sorted((float(v) for v in scores.values()), reverse=True)
        if vals[0] <= 1e-12:
            continue
        if (vals[0] - vals[1]) / vals[0] < 0.22:
            amb += 1
    return amb / float(len(span_outputs))


def _weak_concept_share(cw: dict[str, float]) -> float:
    if not cw:
        return 0.0
    mx = max(float(v) for v in cw.values())
    if mx <= EPS:
        return 0.0
    return sum(1 for v in cw.values() if float(v) < 0.18 * mx) / float(len(cw))


def _mean_best_resolve_score(span_outputs: list[dict[str, Any]]) -> float:
    bests: list[float] = []
    for r in span_outputs:
        scores = r.get("candidate_scores") or {}
        if not scores:
            continue
        bests.append(max(float(v) for v in scores.values()))
    return sum(bests) / len(bests) if bests else 0.0


def _compute_uncertainty_summaries(
    text: str,
    hits: list[Any],
    rejected: list[Any],
    span_outputs: list[dict[str, Any]],
    cw: dict[str, float],
    conc: float,
    disp: float,
    repo: Path,
    mode: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    unmapped = float(compute_lexical_unmapped_token_rate(text, repo_root=repo, mode=mode))
    acc = len(hits)
    rej = len(rejected)
    low_pri = rej / float(max(1, acc + rej))
    fuzzy_amb = _ambiguous_span_ratio(span_outputs)
    lexical_uncertainty_summary = {
        "unmapped_lexical_ratio": round(unmapped, 6),
        "fuzzy_link_ratio": round(fuzzy_amb, 6),
        "alias_link_ratio": 0.0,
        "low_priority_link_ratio": round(low_pri, 6),
    }
    ent = _entropy01_from_concept_weights(cw)
    weak = _weak_concept_share(cw)
    mean_sup = _mean_best_resolve_score(span_outputs)
    concept_uncertainty_summary = {
        "weak_concept_share": round(weak, 6),
        "ambiguous_concept_share": round(fuzzy_amb, 6),
        "concept_entropy": round(ent, 6),
        "mean_concept_support_strength": round(mean_sup, 6),
    }
    concept_support_summary = {
        "mean_best_resolve_score": round(mean_sup, 6),
        "hex_concentration": round(float(conc), 6),
        "hex_dispersion": round(float(disp), 6),
    }
    return lexical_uncertainty_summary, concept_uncertainty_summary, concept_support_summary


def _dlcr_contradiction_alignment_fields(
    conc: float,
    disp: float,
    trajectory: dict[str, Any],
    global_load: float,
) -> dict[str, Any]:
    """Structured DLCR ↔ cross-plane contradiction alignment (metrics only, no narrative)."""
    g = max(0.0, min(1.0, float(global_load)))
    disp_f = max(0.0, min(1.0, float(disp)))
    conc_f = max(0.0, min(1.0, float(conc)))
    seg_ct = max(1.0, float(trajectory.get("segment_count") or 1.0))
    trans_ct = float(trajectory.get("transition_count") or 0.0)
    jump = float(trajectory.get("jump_distance") or 0.0)
    spread_measure = max(
        0.0,
        min(
            1.0,
            0.55 * disp_f
            + 0.25 * min(1.0, trans_ct / max(1.0, seg_ct - 1e-9))
            + 0.2 * min(1.0, jump / 24.0),
        ),
    )
    expected_spread = max(0.0, min(1.0, 0.32 + 0.58 * g))
    spread_vs = abs(spread_measure - expected_spread) <= 0.38
    shape_expected = max(0.0, min(1.0, 1.0 - 1.1 * g))
    shape_vs = abs(conc_f - shape_expected) <= 0.44
    alignment_score = max(0.0, min(1.0, 1.0 - abs(spread_measure - expected_spread)))
    return {
        "spread_vs_contradiction_consistent": bool(spread_vs),
        "shape_vs_contradiction_consistent": bool(shape_vs),
        "alignment_score": round(float(alignment_score), 6),
        "spread_proxy": round(float(spread_measure), 6),
        "expected_spread_proxy": round(float(expected_spread), 6),
    }


def _analyze_internal(
    text: str,
    *,
    repo_root: Path | None = None,
    dict_a_paths: list[Path] | None = None,
    dict_b_paths: list[Path] | None = None,
    anchors_path: Path | None = None,
    mode: str = "clinical_speech",
    contradiction_package: dict[str, Any] | None = None,
    empirical_weight_override: float | None = None,
) -> dict[str, Any]:
    """
    Run DLCR path: normalize → match Dict A → resolve Dict B → project hex → dynamics → aggregate.

    Default assets: merged seed + TFP packs under ``assets/data/engine_dynamics_v060/``.
    """
    empirical_weight = effective_empirical_weight(empirical_weight_override)
    repo = repo_root or _repo_root()
    base = repo / "assets" / "data" / "engine_dynamics_v060"
    calib_a = resolve_dict_file(repo, "dict_a.jsonl")
    calib_b = resolve_dict_file(repo, "dict_b.jsonl")
    # CORE-D2 W8 (CORE-D2-081): load once per runtime context, not per hit/segment.
    # A present file does not enable anything -- resolver.coherence_empirical_weight
    # stays 0.0 in engine_constants.json until the separate W9 activation gate, so
    # dict_d_pairs is threaded through purely as an inert shadow signal until then.
    calib_d = resolve_dict_d_file(repo)
    dict_d_pairs = load_dict_d_pairs(calib_d) if calib_d else {}
    # Legacy ``dict_a_tfp`` before stack layers so ``gold_tfp_ru`` B_A10 winners stay stable;
    # stack rows add non-colliding ``normalized_form`` keys (first path wins per form).
    da_paths_default = [
        base / "dict_a" / "dict_a_seed.jsonl",
        base / "dict_a" / "dict_a_tfp.jsonl",
        base / "dict_a" / "dict_a_tfp_ru_core.jsonl",
        base / "dict_a" / "dict_a_tfp_ru_variants.jsonl",
        base / "dict_a" / "dict_a_tfp_ru_speech.jsonl",
        base / "dict_a" / "dict_a_tfp_ru_negative.jsonl",
        # Corpus LLM align (ru-tfp-align); last so new normalized_form keys fill gaps only (first wins).
        base / "dict_a" / "dict_a_tfp_ru_aligned.jsonl",
    ]
    db_paths_default = [
        base / "dict_b" / "dict_b_seed.jsonl",
        base / "dict_b" / "dict_b_tfp_ru_v060.jsonl",
        base / "dict_b" / "dict_b_tfp.jsonl",
    ]
    da_paths = list(dict_a_paths) if dict_a_paths else ([calib_a] if calib_a else da_paths_default)
    db_paths = list(dict_b_paths) if dict_b_paths else ([calib_b] if calib_b else db_paths_default)
    anch = anchors_path or (base / "anchors" / "concept_hex_anchors_tfp.json")
    if not anch.exists():
        anch = base / "anchors" / "concept_hex_anchors.json"

    dict_a = _merge_dict_a(da_paths)
    anchor_registry = json.loads(anch.read_text(encoding="utf-8")) if anch.exists() else {}
    dict_b_rows = _merge_dict_b(db_paths)
    dict_b_rows = [row for row in dict_b_rows if str(row.get("concept_id") or "") in anchor_registry]
    concept_index = {row["concept_id"]: row for row in dict_b_rows}

    pins = _load_version_pins(repo)
    pol = load_dlcr_policy(repo)
    engine_cfg = load_engine_signal_calibration()
    max_acc: int | None
    raw_max = pol.get("dict_a_max_accepted")
    env_max = os.environ.get("HESPERIA_DICT_A_MAX_ACCEPTED", "").strip()
    if env_max.isdigit():
        max_acc = int(env_max)
    elif raw_max is not None and str(raw_max).strip().lstrip("-").isdigit():
        max_acc = int(raw_max)
    else:
        max_acc = None
    diversity_key = _hit_family_diversity_key if pol.get("dict_a_family_diversity") else None
    smooth_alpha = float(engine_cfg.get("hex_smoothing_alpha") or pol.get("hex_smooth_alpha") or 0.0)
    hex_decay = float(engine_cfg.get("hex_decay") or get_constant("operator.decay_default", 0.05))
    ctx_win = int(pol.get("resolver_context_window") or 48)
    seq_w = float(pol.get("sequential_association_weight") or 0.04)
    cooc_window = int(pol.get("cooc_window") or 4)
    min_token_len = int(os.environ.get("HESPERIA_DLCR_MIN_TOKEN_LEN", "2") or 2)
    min_resolve_score = float(os.environ.get("HESPERIA_DLCR_MIN_RESOLVE_SCORE", "0.5") or 0.5)
    stopwords = _load_runtime_stopwords()
    domain_whitelist = _load_domain_whitelist()

    canonical, _prep_meta = prepare_structural_analysis_text(text, policy_mode=mode)
    norm = normalize_text(canonical)
    pair_counts = pair_counts_from_canonical(norm["canonical_text"], window=cooc_window)
    top_pairs = sorted(pair_counts.items(), key=lambda x: (-x[1], x[0]))[:24]

    hits, rejected = match_dict_a(
        norm["canonical_text"], dict_a, max_accepted=max_acc, diversity_key=diversity_key
    )

    # CORE-D2 W8 (CORE-D2-082/083/084): baseline pass, paragraph-grouped, builds each
    # hit's empirical context per the W0 two-pass runtime context contract -- kept
    # separate from the sequential loop below so the pre-existing, unrelated
    # sequential-association-boost/recent_winners mechanics stay byte-for-byte
    # unchanged. A hit the main loop would filter out (stopword/domain-whitelist)
    # contributes no baseline winner, matching that it never reaches recent_winners
    # either.
    para_spans = paragraph_spans(norm["canonical_text"])
    hit_paragraph = [paragraph_index_for_span(para_spans, h.span_start) for h in hits]
    hits_by_paragraph: dict[int, list[int]] = {}
    for idx, p_idx in enumerate(hit_paragraph):
        hits_by_paragraph.setdefault(p_idx, []).append(idx)
    baseline_winner_by_hit: dict[int, str | None] = {}
    for idx, hit in enumerate(hits):
        if _drop_low_quality_token(
            hit.matched_text,
            stopwords=stopwords,
            min_len=min_token_len,
            domain_whitelist=domain_whitelist,
        ):
            baseline_winner_by_hit[idx] = None
            continue
        baseline = resolve_hit(
            hit,
            concept_index,
            mode=mode,
            version="v0.6.0",
            canonical_text=norm["canonical_text"],
            context_window=ctx_win,
            dict_d_pairs=None,
            empirical_context_ids=frozenset(),
            empirical_weight_override=empirical_weight,
        )
        baseline_winner_by_hit[idx] = baseline["winning_concept_id"]

    span_outputs: list[dict[str, Any]] = []
    unresolved_span_outputs: list[dict[str, Any]] = []
    recent_winners: list[str] = []
    for hit_idx, hit in enumerate(hits):
        if _drop_low_quality_token(
            hit.matched_text,
            stopwords=stopwords,
            min_len=min_token_len,
            domain_whitelist=domain_whitelist,
        ):
            continue
        ab: dict[str, float] = {}
        if seq_w > 0 and recent_winners:
            for cid in hit.candidate_concept_ids:
                boost = 0.0
                for prev in recent_winners[-3:]:
                    if prev == str(cid):
                        continue
                    boost += seq_w
                if boost > 0:
                    ab[str(cid)] = boost
        empirical_context_ids = frozenset(
            str(baseline_winner_by_hit[i])
            for i in hits_by_paragraph[hit_paragraph[hit_idx]]
            if i != hit_idx and baseline_winner_by_hit[i] is not None
        )
        r = resolve_hit(
            hit,
            concept_index,
            mode=mode,
            version="v0.6.0",
            canonical_text=norm["canonical_text"],
            context_window=ctx_win,
            association_boost=ab or None,
            dict_d_pairs=dict_d_pairs,
            empirical_context_ids=empirical_context_ids,
            empirical_weight_override=empirical_weight,
        )
        r, is_resolved = _classify_span_resolution(
            r,
            min_resolve_score=min_resolve_score,
        )
        if not is_resolved:
            unresolved_span_outputs.append(r)
            continue
        span_outputs.append(r)
        w = r.get("winning_concept_id")
        if w:
            recent_winners.append(str(w))

    concept_weights_raw = _concept_weights_from_resolutions(
        span_outputs,
        top_k=int(os.environ.get("HESPERIA_DLCR_TOKEN_TOPK", "3") or 3),
        debug=os.environ.get("HESPERIA_DLCR_DEBUG_TOKEN_WEIGHTS", "").strip().lower()
        in {"1", "true", "yes"},
    )
    concept_weights_stabilized = _stabilize_concept_weights(
        concept_weights_raw,
        token_count=len(norm["canonical_text"].split()),
        concept_cap=float(engine_cfg.get("concept_cap") or 8.0),
        log_normalization_enabled=bool(engine_cfg.get("log_normalization_enabled")),
    )
    evidence_counts: Counter[str] = Counter()
    for r in span_outputs:
        w = r.get("winning_concept_id")
        if w:
            evidence_counts[str(w)] += 1
    cd_on = os.environ.get("HESPERIA_CD_ENABLED", "").strip().lower() in {"1", "true", "yes"}
    cd_off = os.environ.get("HESPERIA_CD_DISABLE", "").strip().lower() in {"1", "true", "yes"}
    if cd_on and not cd_off:
        cd_env = os.environ.get("HESPERIA_CD_JSONL", "").strip()
        cd_path = Path(cd_env) if cd_env else default_cd_path(repo)
        try:
            cd_phase = int(os.environ.get("HESPERIA_CD_PHASE", "1") or "1")
        except ValueError:
            cd_phase = 1
        if cd_path.is_file():
            concept_weights_stabilized = apply_cd_phase1(
                concept_weights_stabilized,
                dict(evidence_counts),
                cd_path,
                cd_phase=max(1, cd_phase),
            )
    state_raw, state_post, cw, deg_proj, invariants = _post_hex_concept_feedback(
        concept_weights_stabilized,
        anchor_registry=anchor_registry,
        hex_decay=hex_decay,
        hex_smooth_alpha=smooth_alpha,
    )
    conc = concentration_index(state_post)
    disp = dispersion_index(state_post)
    fam_d, area_d = aggregate_hex_state(cw, concept_index)
    fam_raw, area_raw = aggregate_hex_state(concept_weights_stabilized, concept_index)
    cross_fam = cross_family_relation_sketch(fam_d, top_k=8)

    hits_288 = [0.0] * 288
    for cid, weight in cw.items():
        meta = concept_index.get(cid) or {}
        for fid in meta.get("family_ids") or []:
            for aid in meta.get("area_ids") or []:
                idx = _family_slot_index(str(aid), str(fid))
                if idx is not None and 0 <= idx < 288:
                    hits_288[idx] += float(weight)

    # Segment trajectory + hex geometry per segment (PO-14 / PO-18)
    seg_summaries: list[dict[str, Any]] = []
    seg_drifts: list[float] = []
    seg_persist: list[float] = []
    prev_map: dict[str, float] = {}
    segment_state = SemanticState(position=dict(anchor_registry))
    for _s, _e, seg in segment_by_newlines(text):
        sn = normalize_text(seg)
        sh, _ = match_dict_a(
            sn["canonical_text"], dict_a, max_accepted=max_acc, diversity_key=diversity_key
        )
        seg_cw: dict[str, float] = {}
        # CORE-D2 W8 (CORE-D2-082/083): one newline-delimited segment is already one
        # natural paragraph grouping -- resolve it in a single two-pass batch per the
        # W0 runtime context contract, instead of per-hit with no cross-hit context.
        filtered_hits = [
            hit
            for hit in sh
            if not _drop_low_quality_token(
                hit.matched_text,
                stopwords=stopwords,
                min_len=min_token_len,
                domain_whitelist=domain_whitelist,
            )
        ]
        seg_results = resolve_paragraph_hits(
            filtered_hits,
            concept_index,
            mode=mode,
            version="v0.6.0",
            canonical_text=sn["canonical_text"],
            context_window=ctx_win,
            dict_d_pairs=dict_d_pairs,
            empirical_weight_override=empirical_weight,
        )
        for r in seg_results:
            best_score = max((float(v) for v in (r.get("candidate_scores") or {}).values()), default=0.0)
            if best_score < min_resolve_score:
                continue
            cid = r.get("winning_concept_id")
            if cid:
                seg_cw[str(cid)] = seg_cw.get(str(cid), 0.0) + 1.0
        hs, _ = project_concepts_to_hex(seg_cw, anchor_registry, return_state=True)
        segment_state, seg_invariants = _evolve_segment_state(
            segment_state,
            seg_cw,
            anchor_registry=anchor_registry,
            smooth_alpha=smooth_alpha,
        )
        seg_drifts.append(quantize(l1_drift(prev_map, segment_state.mass_vector)))
        seg_persist.append(quantize(persistence_score(prev_map, segment_state.mass_vector)))
        prev_map = dict(segment_state.mass_vector)
        dom_slot = None
        mass = 0.0
        if hs.mass_vector:
            dom_sym = max(hs.mass_vector, key=lambda k: hs.mass_vector[k])
            mass = float(hs.mass_vector[dom_sym])
            try:
                mp = load_hex_index_map(base / "anchors" / "hex_index_map.json")
                dom_slot = mp.get(dom_sym)
            except Exception:
                dom_slot = None
        seg_summaries.append({"dominant_slot": dom_slot, "mass": mass, "invariants": seg_invariants})
    traj = trajectory_over_segments(seg_summaries)

    _ = (pins, top_pairs, cross_fam, hits, rejected, span_outputs, cw, concept_weights_raw, concept_weights_stabilized, state_raw, state_post, conc, disp, fam_raw, area_raw, deg_proj, seg_persist)
    failure_flags = classify_failures(
        {
            "segment_trajectory": traj,
            "hex_concentration": quantize(conc),
            "hex_dispersion": quantize(disp),
        }
    )
    if invariants:
        failure_flags = sorted(set(failure_flags + ["drift"]))
    result = build_result(
        area_activation={k: quantize(v) for k, v in sorted(area_d.items())},
        family_activation={k: quantize(v) for k, v in sorted(fam_d.items())},
        trajectory=traj,
        segment_drifts=[quantize(x) for x in seg_drifts],
        failure_flags=failure_flags,
    )
    guard_determinism(result)
    # Keep legacy DLCR fields for calibration/eval tooling.
    result["run"] = "dlcr_pipeline_v1"
    result["concept_weights"] = {k: quantize(v) for k, v in sorted(cw.items())}
    result["family_activation"] = {k: quantize(v) for k, v in sorted(fam_d.items())}
    result["area_activation"] = {k: quantize(v) for k, v in sorted(area_d.items())}
    result["lexical_hits_accepted"] = len(hits)
    result["lexical_hits_rejected"] = len(rejected)
    result["canonical_text"] = norm["canonical_text"]
    result["span_resolutions"] = span_outputs
    result["unresolved_span_resolutions"] = unresolved_span_outputs
    result["resolver_trace"] = {
        "dict_d_effective_weight": empirical_weight,
        "dict_d_pairs_loaded": len(dict_d_pairs),
    }
    result["calibration_dicts"] = calibration_manifest(repo)
    result["hex_concentration_index"] = quantize(conc)
    result["hex_dispersion_index"] = quantize(disp)
    lex_u, con_u, sup_u = _compute_uncertainty_summaries(
        text, hits, rejected, span_outputs, cw, conc, disp, repo, mode
    )
    result["lexical_uncertainty_summary"] = lex_u
    result["concept_uncertainty_summary"] = con_u
    result["concept_support_summary"] = sup_u
    ct_for_neg = str(norm.get("canonical_text") or "")
    try:
        neg_blocks = _collect_negative_blocks(ct_for_neg, dict_a)
        neg_cov = sum(max(0, int(e) - int(s)) for s, e in neg_blocks)
        negated_marker_ratio = min(1.0, float(neg_cov) / float(max(1, len(ct_for_neg))))
    except Exception:
        negated_marker_ratio = 0.0
    result["negation_summary"] = {
        "negated_marker_ratio": round(float(negated_marker_ratio), 6),
        "negated_concept_ratio": 0.0,
        "concept_negation_burden": {},
    }
    # CHI-004: surface family-hits vector for Field Dynamics DLCR blend (e2e_bridge).
    result["family_hits_288"] = [round(float(x), 6) for x in hits_288]
    apply_crossplane_contradiction_fields_to_dlcr_result(result, contradiction_package)
    return result


def run_dlcr_pipeline(
    text: str,
    *,
    repo_root: Path | None = None,
    dict_a_paths: list[Path] | None = None,
    dict_b_paths: list[Path] | None = None,
    anchors_path: Path | None = None,
    mode: str = "clinical_speech",
    contradiction_package: dict[str, Any] | None = None,
    empirical_weight_override: float | None = None,
) -> dict[str, Any]:
    return _analyze_internal(
        text,
        repo_root=repo_root,
        dict_a_paths=dict_a_paths,
        dict_b_paths=dict_b_paths,
        anchors_path=anchors_path,
        mode=mode,
        contradiction_package=contradiction_package,
        empirical_weight_override=empirical_weight_override,
    )


def analyze(text: str) -> dict[str, Any]:
    from core.runtime.engine import analyze_engine

    return analyze_engine(text)
