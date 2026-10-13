from __future__ import annotations

import json

import pytest

from core.engine.lexical_concept import pipeline
from core.lexical.matcher import LexicalHit
from core.resolver.context import coherence_from_empirical
from core.resolver.dict_d_index import load_dict_d_pairs
from core.resolver.resolver import resolve_hit
from core.resolver.score_rules import score_candidate


def test_coherence_from_empirical_inert_without_index() -> None:
    assert coherence_from_empirical("C-A", frozenset({"C-B"}), dict_d_pairs=None) == 0.0
    assert coherence_from_empirical("C-A", frozenset(), dict_d_pairs={("C-A", "C-B"): 0.9}) == 0.0


def test_coherence_from_empirical_finds_pair_either_key_order() -> None:
    pairs = {("C-A", "C-B"): 0.42}
    assert coherence_from_empirical("C-A", frozenset({"C-B"}), dict_d_pairs=pairs) == 0.42
    assert coherence_from_empirical("C-B", frozenset({"C-A"}), dict_d_pairs=pairs) == 0.42


def test_coherence_from_empirical_clamps_negative_to_zero() -> None:
    pairs = {("C-A", "C-B"): -0.3}
    assert coherence_from_empirical("C-A", frozenset({"C-B"}), dict_d_pairs=pairs) == 0.0


def test_coherence_from_empirical_picks_strongest_sibling() -> None:
    pairs = {("C-A", "C-B"): 0.1, ("C-A", "C-C"): 0.8}
    assert coherence_from_empirical("C-A", frozenset({"C-B", "C-C"}), dict_d_pairs=pairs) == 0.8


def test_load_dict_d_pairs_round_trip(tmp_path) -> None:
    p = tmp_path / "dict_d.jsonl"
    p.write_text(
        "\n".join(
            [
                json.dumps({"concept_id_a": "C-B", "concept_id_b": "C-A", "npmi": 0.5}),
                json.dumps({"concept_id_a": "C-X", "npmi": 0.9}),  # missing concept_id_b, skipped
                "",
            ]
        ),
        encoding="utf-8",
    )
    pairs = load_dict_d_pairs(p)
    assert pairs == {("C-A", "C-B"): 0.5}


def test_load_dict_d_pairs_missing_file_returns_empty(tmp_path) -> None:
    assert load_dict_d_pairs(tmp_path / "nope.jsonl") == {}


def test_score_candidate_empirical_boost_inert_at_live_default_weight() -> None:
    """resolver.coherence_empirical_weight is 0.0 in engine_constants.json today —
    passing a nonzero empirical_boost must not move the score until that flips."""
    base = score_candidate("exact", priority=5, specificity_rank=3, context_overlap=2, empirical_boost=0.0)
    boosted = score_candidate("exact", priority=5, specificity_rank=3, context_overlap=2, empirical_boost=1.0)
    assert base == boosted


def test_resolve_hit_identical_with_or_without_dict_d_pairs() -> None:
    """CHI-015 O4 wiring must be a no-op on live output until the weight is flipped —
    same hit, same concept_index, only dict_d_pairs differs."""
    hit = LexicalHit(
        entry_id="A-1",
        matched_text="identity diffusion",
        span_start=0,
        span_end=18,
        match_type="phrase",
        candidate_concept_ids=["C-LOW", "C-HIGH"],
        priority=10,
    )
    concept_index = {
        "C-LOW": {"specificity_rank": 2, "preferred_label": "low"},
        "C-HIGH": {"specificity_rank": 7, "preferred_label": "high"},
    }
    without = resolve_hit(hit, concept_index, mode="clinical_speech")
    with_pairs = resolve_hit(
        hit,
        concept_index,
        mode="clinical_speech",
        dict_d_pairs={("C-HIGH", "C-LOW"): 0.99},
    )
    assert without["candidate_scores"] == with_pairs["candidate_scores"]
    assert without["winning_concept_id"] == with_pairs["winning_concept_id"]


def test_score_candidate_explicit_zero_override_blocks_nonzero_runtime_weight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_get_constant = pipeline.get_constant

    def nonzero_empirical_config(key: str, default: float) -> float:
        if key == "resolver.coherence_empirical_weight":
            return 0.75
        return real_get_constant(key, default)

    monkeypatch.setattr(
        "core.resolver.score_rules.get_constant",
        nonzero_empirical_config,
    )
    baseline = score_candidate(
        "exact",
        priority=5,
        specificity_rank=3,
        context_overlap=2,
        empirical_boost=0.0,
        empirical_weight_override=0.0,
    )
    blocked = score_candidate(
        "exact",
        priority=5,
        specificity_rank=3,
        context_overlap=2,
        empirical_boost=1.0,
        empirical_weight_override=0.0,
    )
    ambient = score_candidate(
        "exact",
        priority=5,
        specificity_rank=3,
        context_overlap=2,
        empirical_boost=1.0,
    )

    assert blocked == baseline
    assert ambient > blocked


def test_resolve_hit_reports_explicit_empirical_weight_override() -> None:
    hit = LexicalHit(
        entry_id="A-1",
        matched_text="identity diffusion",
        span_start=0,
        span_end=18,
        match_type="phrase",
        candidate_concept_ids=["C-LOW", "C-HIGH"],
        priority=10,
    )
    output = resolve_hit(
        hit,
        {
            "C-LOW": {"specificity_rank": 2},
            "C-HIGH": {"specificity_rank": 7},
        },
        dict_d_pairs={("C-HIGH", "C-LOW"): 0.99},
        empirical_weight_override=0.0,
    )

    assert output["audit"]["dict_d_effective_weight"] == 0.0


def test_pipeline_threads_empirical_override_to_both_resolver_call_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[float | None] = []
    real_resolve_hit = pipeline.resolve_hit

    def recording_resolve_hit(*args, **kwargs):
        calls.append(kwargs.get("empirical_weight_override"))
        return real_resolve_hit(*args, **kwargs)

    monkeypatch.setattr(pipeline, "resolve_hit", recording_resolve_hit)
    output = pipeline.run_dlcr_pipeline(
        "перенос\nперенос",
        empirical_weight_override=0.0,
    )

    assert len(calls) >= 2
    assert set(calls) == {0.0}
    assert output["resolver_trace"]["dict_d_effective_weight"] == 0.0
