"""Deterministic lexical-candidate to concept resolver."""

from __future__ import annotations

from typing import Any

from core.lexical.matcher import LexicalHit
from core.resolver.context import (
    coherence_from_empirical_traced,
    coherence_from_related,
    label_token_overlap,
)
from core.resolver.score_rules import (
    effective_empirical_weight,
    saturate,
    score_candidate,
)
from core.resolver.tiebreaks import break_tie


def resolve_hit(
    hit: LexicalHit,
    concept_index: dict[str, dict],
    mode: str = "default",
    version: str = "v0.6.0",
    *,
    canonical_text: str | None = None,
    context_window: int = 48,
    association_boost: dict[str, float] | None = None,
    dict_d_pairs: dict[tuple[str, str], float] | None = None,
    empirical_context_ids: frozenset[str] | None = None,
    empirical_weight_override: float | None = None,
) -> dict[str, Any]:
    """
    Resolve a single lexical hit to a winning concept (Ethan PO-05–PO-09).

    ``canonical_text`` enables deterministic context overlap (PO-07).
    ``association_boost`` adds bounded prior mass from co-occurrence layer (PO-23).
    ``dict_d_pairs`` (CHI-015 O4): optional {(concept_id_a, concept_id_b): npmi}
    from ``core.resolver.dict_d_index.load_dict_d_pairs``.

    ``empirical_context_ids`` (CORE-D2 W8): the CORE-D2 W0 runtime context
    contract's paragraph context — deduplicated baseline-winning concept IDs
    from *other* hits in the same paragraph. Deliberately a separate
    parameter from the same-hit ``candidate_concept_ids`` siblings used by
    ``coherence_from_related`` — same-hit siblings are forbidden as empirical
    context. Defaults to an empty set (no empirical signal) when not
    supplied; use :func:`resolve_paragraph_hits`, not this function directly,
    to construct it correctly via the required two-pass process. With
    ``resolver.coherence_empirical_weight`` at its live default of 0.0,
    passing this or not currently makes zero difference to any live score —
    see ``coherence_from_empirical``'s docstring.
    """
    empirical_weight = effective_empirical_weight(empirical_weight_override)
    association_boost = association_boost or {}
    siblings = frozenset(str(x) for x in hit.candidate_concept_ids)
    empirical_context = empirical_context_ids if empirical_context_ids is not None else frozenset()
    candidate_activation: dict[str, float] = {}
    candidate_detail: list[dict[str, Any]] = []

    for concept_id in hit.candidate_concept_ids:
        concept = concept_index.get(concept_id, {})
        ctx_n = 0
        if canonical_text:
            label = str(concept.get("preferred_label") or "")
            ctx_n = label_token_overlap(
                canonical_text, hit.span_start, hit.span_end, label, window=context_window
            )
        coh = coherence_from_related(concept_id, concept_index, sibling_ids=siblings)
        emp, emp_pair = coherence_from_empirical_traced(concept_id, empirical_context, dict_d_pairs=dict_d_pairs)
        boost = float(association_boost.get(concept_id, 0.0))
        activation = score_candidate(
            match_type=hit.match_type,
            priority=hit.priority,
            specificity_rank=int(concept.get("specificity_rank", 0)),
            context_overlap=ctx_n,
            coherence_boost=coh,
            empirical_boost=emp,
            empirical_weight_override=empirical_weight,
        )
        activation = saturate(activation + max(0.0, min(1.0, boost)))
        candidate_activation[concept_id] = activation
        candidate_detail.append(
            {
                "concept_id": concept_id,
                "activation": round(activation, 6),
                "score": round(activation, 6),  # compatibility mirror
                "context_overlap": ctx_n,
                "coherence_boost": round(coh, 6),
                "empirical_boost": round(emp, 6),
                "empirical_pair_concept_id": emp_pair,
                "association_boost": round(boost, 6),
            }
        )

    if not candidate_activation:
        winner = None
        reasons = ["no_candidates"]
        rejected = ["no_candidate_activation"]
    else:
        top_score = max(candidate_activation.values())
        top_candidates = [cid for cid, val in candidate_activation.items() if val == top_score]
        if len(top_candidates) == 1:
            winner = top_candidates[0]
            reasons = ["top_score_unique"]
        else:
            winner = break_tie(top_candidates, concept_index)
            reasons = ["top_score_tie", "tiebreak_specificity_then_lexical_id"]
        rejected = [f"candidate_rejected:{cid}" for cid in candidate_activation if cid != winner]

    return {
        "source_text_span": hit.matched_text,
        "source_char_start": hit.span_start,
        "source_char_end": hit.span_end,
        "normalized_span": hit.matched_text,
        "lexical_entry_ids": [hit.entry_id],
        "candidate_concepts": list(hit.candidate_concept_ids),
        "candidate_scores": {k: round(v, 6) for k, v in candidate_activation.items()},
        "winning_concept_id": winner,
        "winning_reason_codes": reasons,
        "rejected_reason_codes": rejected,
        "rule_trace": [
            "phrase-first",
            "match-strength",
            "context_overlap",
            "coherence_related",
            "association_boost_optional",
            "tiebreak_specificity_lexical",
        ],
        "audit": {
            "candidates_detail": candidate_detail,
            "tie_break_rule": "specificity_rank_desc_then_concept_id_lex",
            "dict_d_effective_weight": empirical_weight,
            "dict_d_pairs_supplied": dict_d_pairs is not None,
            "empirical_context_size": len(empirical_context),
        },
        "mode": mode,
        "version": version,
    }


def resolve_paragraph_hits(
    hits: list[LexicalHit],
    concept_index: dict[str, dict],
    mode: str = "default",
    version: str = "v0.6.0",
    *,
    canonical_text: str | None = None,
    context_window: int = 48,
    association_boost: dict[str, float] | None = None,
    dict_d_pairs: dict[tuple[str, str], float] | None = None,
    empirical_weight_override: float | None = None,
) -> list[dict[str, Any]]:
    """
    Resolve every hit in ONE paragraph via the CORE-D2 W0 two-pass runtime
    context contract (``ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md``,
    "Runtime context contract"):

    1. Baseline pass — resolve every hit with no empirical context
       (``empirical_context_ids=frozenset()``), giving each hit's baseline
       winning concept.
    2. Empirical pass — rescore each hit using the deduplicated baseline
       winners from every *other* hit in this paragraph as its empirical
       context; no hit ever sees its own baseline winner or feeds back into
       itself.

    All ``hits`` passed in are assumed to already belong to one paragraph —
    callers are responsible for paragraph grouping (see
    ``core.resolver.context.paragraph_spans``/``paragraph_index_for_span``).

    Invariant (CORE-D2-088): at ``resolver.coherence_empirical_weight == 0.0``
    (the live default), pass 2's results are identical to pass 1's — the
    weight zeroes ``empirical_boost``'s contribution in ``score_candidate``
    regardless of what context was computed, so this is always true, not
    just true for a "well-behaved" corpus.
    """
    baseline = [
        resolve_hit(
            hit,
            concept_index,
            mode,
            version,
            canonical_text=canonical_text,
            context_window=context_window,
            association_boost=association_boost,
            dict_d_pairs=None,
            empirical_context_ids=frozenset(),
            empirical_weight_override=empirical_weight_override,
        )
        for hit in hits
    ]
    baseline_winners = [r["winning_concept_id"] for r in baseline]

    final: list[dict[str, Any]] = []
    for i, hit in enumerate(hits):
        context_ids = frozenset(
            str(w) for j, w in enumerate(baseline_winners) if j != i and w is not None
        )
        final.append(
            resolve_hit(
                hit,
                concept_index,
                mode,
                version,
                canonical_text=canonical_text,
                context_window=context_window,
                association_boost=association_boost,
                dict_d_pairs=dict_d_pairs,
                empirical_context_ids=context_ids,
                empirical_weight_override=empirical_weight_override,
            )
        )
    return final

