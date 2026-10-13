# Ethan contract — CORE-D2 W7 sampling and graph stability

**Task:** `CORE-D2-070`
**Date:** 2026-09-16
**Status:** RATIFIED
**Parent contract:** `ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md`
**Authority note:** Felix, playing the Ethan role, explicit operator authorization ("execute solo through activation," 2026-09-16).

Operationalizes CHI-015 §7's prose discipline ("pull N random high-NPMI
`novel` pairs and N random authored-edge-disagreement pairs, human-check
against source excerpts"; "does the graph change wildly if a book is dropped
or the corpus grows") into concrete, testable numbers. Nothing here was
written down anywhere before this task — flagged explicitly per the
2026-09-16 blocker assessment (`CHIRON-CORE-S2-LIVE-04-GATE-ASSESSMENT-2026-09-16.md`)
that first found this gap.

## Sample sizes and strata

Two strata, sample size **25** each (fixed; if a stratum has fewer than 25
eligible rows, take all of them — never pad, never error):

1. **High-NPMI novel** — rows with `agreement_with_b == "novel"` and
   `npmi >= 0.3`. Rationale for `0.3`: roughly the top quartile of the
   theoretically achievable `[-1, 1]` NPMI range for a *positive*,
   non-trivial association; low enough to catch real signal, high enough to
   exclude noise-floor co-occurrence.
2. **Authored-edge disagreement** — rows with `agreement_with_b == "agrees"`
   (i.e. Dict B claims an authored relation) and `npmi <= 0.0` — the corpus
   shows no positive empirical support for a claimed relation. (A pair with
   an authored relation but literally zero observed co-occurrence never
   becomes a Dict D row at all under the W5 builder, since rows are only
   emitted for `n_ij > 0`; that class — authored relations with *zero*
   evidence — is reported separately as a count, not sampled as pairs, since
   there is no co-occurrence data to attach a source excerpt to.)

Sampling within a stratum is **seeded random sampling without replacement**,
`random.Random(seed=20260916).sample(...)`, from the stratum's rows sorted
into canonical `(concept_id_a, concept_id_b)` order first (so the sample is
reproducible regardless of upstream row order). `20260916` is this
contract's ratification date as `YYYYMMDD` — arbitrary but fixed and
disclosed, not tuned after seeing results.

## Source excerpt attachment

For each sampled pair, attach **one** excerpt: the first paragraph (by
canonical `(book_id, source_ordinal)` order) in the resolved-corpus export
where both concepts of the pair appear as `winning_concept_id` on some
resolved span. Excerpt record = `{pair, book_id, paragraph_id, text}`. A
sampled pair with no locatable co-occurring paragraph (should not happen —
by construction every Dict D row's `cooc_count >= 1` came from at least one
real paragraph) fails closed rather than shipping an excerpt-less sample row.

## Review disposition format (Colombo role)

One JSON record per sampled pair:
`{pair, stratum, excerpt, disposition: "plausible"|"implausible"|"needs_context", note}`.
This task only builds and exercises the format on synthetic fixtures — real
content judgment requires real corpus text, which does not exist yet (see
`CHIRON-CORE-D2-W5-DICT-D-BUILDER-GATE-REPORT.md`, "What this does not cover
yet"). No synthetic disposition is release evidence.

## Graph stability — leave-one-book-out and corpus-growth perturbation

For a corpus of `K` books, run `K` perturbed rebuilds, each with exactly one
book removed, plus (when a growth fixture is supplied) one rebuild with an
additional book appended. For each perturbed rebuild, compare against the
unperturbed baseline using four metrics computed over the **intersection**
of pairs present in both (a pair present only in one side is reported
separately as `appeared`/`disappeared`, not scored):

1. **Rank correlation** — Spearman's ρ over NPMI rank across the shared
   pairs.
2. **NPMI drift** — mean absolute NPMI delta over the shared pairs.
3. **Significance drift** — mean absolute G² delta over the shared pairs
   (dimensionless comparison is not meaningful across corpus sizes since G²
   scales with `N`; reported as a ratio: mean absolute
   `(g2_perturbed - g2_baseline) / max(g2_baseline, 1.0)`).
4. **Dominance / edge persistence** — Jaccard overlap of the baseline's
   top-50-by-NPMI pair set vs. the perturbed rebuild's top-50-by-NPMI pair
   set (`|intersection| / |union|`).

## Frozen stability pass thresholds (this wave's gate, not W9's activation weight)

A perturbation **passes** stability review when, against the baseline:

- rank correlation ≥ **0.85**;
- mean absolute NPMI drift ≤ **0.10**;
- mean absolute G² drift ratio ≤ **0.50**;
- top-50 Jaccard overlap ≥ **0.60**.

**Any single perturbed rebuild failing any one threshold fails the whole W7
gate** — one unstable book is enough to withhold sign-off, matching the
parent contract's fail-closed discipline. These are graph-stability
acceptance numbers only; they say nothing about what non-zero
`coherence_empirical_weight` value would be safe to activate — that
selection is `CORE-D2-090`'s job, in W9, against real data, and is not
pre-committed here.

## What this contract does not decide

- The actual sample content review (needs real corpus data).
- The W9 activation weight value.
- Whether corpus-growth perturbation is mandatory for every future rebuild
  or a one-time W7 check — left to operator discretion post-activation;
  leave-one-book-out is the mandatory recurring check, growth is exercised
  once here as a fixture-level capability proof.

---
SIGNED: Felix (Ethan role, explicit operator authorization) | Claude Code context | 2026-09-16 | CORE-D2-070
