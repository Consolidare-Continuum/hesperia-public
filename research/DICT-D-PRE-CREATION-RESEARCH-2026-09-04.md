# Dict D pre-creation research — preserved snapshot, 2026-09-04

**Status**: preserved reference artifact, **pre-real-D-creation**. Since this
snapshot, a 9,076-row mock Dict D artifact and inert loader/scoring scaffolding
were committed. They do not implement the CHI-015 design: the artifact was not
built from paragraph-ordered resolved concept sequences, the builder is absent
from the tracked tree, sample/stability gates are prose-only, and no live
pipeline caller loads Dict D. This file remains the point-in-time code research
that grounded CHI-015 §8a; it is not evidence that a releasable Dict D exists.
Current authority is
[`docs/specs/ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md`](../docs/specs/ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md)
and the `CORE-D2-000..099` program. The mock artifact remains non-releasable
with `resolver.coherence_empirical_weight = 0.0`.

Location note: this lives in dev (`igareosh/hesperia`) `research/` — the only `research/` folder
that exists, mirrored to prod (`Consolidare-Continuum/hesperia`) only via the gated
`mirror-atomic-to-cc-srl.sh` promotion, never edited in prod directly.

Repo researched: `/data/hesperia/hesperia`. No files were written or edited during the research
pass itself (research-only).

---

## Key code read (for citation)

- `core/resolver/resolver.py:1-105` (`resolve_hit`)
- `core/resolver/context.py:1-39` (`coherence_from_related`, `label_token_overlap`)
- `core/resolver/score_rules.py:1-47` (`score_candidate`, `saturate`)
- `core/resolver/tiebreaks.py:1-25` (`break_tie`)
- `core/engine/lexical_concept/pipeline.py:596-874` (`_analyze_internal`), `:203-291`
  (`_concept_weights_from_resolutions`, `_stabilize_concept_weights`)
- `core/lexical/cooccurrence.py:1-31`
- `assets/data/engine_dynamics_v060/dlcr_policy.yaml:1-9`
- `assets/config/engine_constants.json` (`resolver.*` node)
- `core/hexmap/projection.py:10-40` (`project_concepts_to_hex`)
- `core/propagation/invariant_enforcer.py:1-193`
- `hesperia/engine/concept_dictionary/validator.py:1-70`
- `core/dynamics/numeric.py:37-40` (`clamp01`)
- `hesperia/extensions/triz/contradiction_feedback.py:23-24`, `core/engine/projection/dlcr_public.py:16-22`
- `docs/foundations/genesis_taxonomy_provenance.md:65-90`
- `docs/recipes/chiron_tweaks/CHI-015-dict-d-concept-cooccurrence-spec.md` (full),
  `docs/foundations/corners/lexicon_resolver.md` (full)

## 1. `coherence_from_related`, exactly as implemented

`core/resolver/context.py:26-39`:

```python
def coherence_from_related(concept_id, concept_index, *, sibling_ids: frozenset[str]) -> float:
    meta = concept_index.get(concept_id) or {}
    related = frozenset(str(x) for x in (meta.get("related_concept_ids") or []) if x)
    if not related or not sibling_ids:
        return 0.0
    return 0.15 * float(len(related & sibling_ids))
```

It is **graded by count, not binary**: `0.15 * |related_concept_ids ∩ other candidates in the same
LexicalHit|`. Each edge contributes a flat, unweighted 0.15 — `related_concept_ids` itself carries
no per-edge weight (confirmed in `assets/schemas/lexical_concept/dict_b.schema.json:75-80`, plain
`array<string>`). The raw value is **not independently clamped**; it flows into `score_rules.py:35-39`:

```python
local_signal = clamp01(
    (context_overlap / context_overlap_norm) + coherence_boost + locality * 0.2
)
```

So `coherence_boost` is summed additively with `context_overlap` and a fixed `locality*0.2` term,
and the *sum* is clamped to `[0,1]` via `clamp01` (`core/dynamics/numeric.py:37-40`, which also
absorbs NaN/Inf → 0.0). `local_signal` is then weighted by `weight_locality=0.2`
(`assets/config/engine_constants.json`, `resolver` node) inside the final `score_candidate` blend
(`w1*relevance + w2*specificity + w3*local_signal`). **There is no existing per-component weight
isolated to `coherence_boost` alone** — only the aggregate `local_signal` has a dedicated
multiplier.

## 2. Downstream consumers of `resolve_hit`'s output

`resolve_hit` returns `candidate_scores`, `winning_concept_id`, `rule_trace`,
`winning_reason_codes`, `audit.candidates_detail` (`core/resolver/resolver.py:79-104`).

Traced every consumer of `span_resolutions` (grep across repo, `tools/*`,
`core/engine/projection/dlcr_public.py`, `hesperia/extensions/triz/contradiction_feedback.py`,
`runtime/pipeline/*`):

- `core/engine/lexical_concept/pipeline.py:227-258` (`_concept_weights_from_resolutions`) — reads
  **only `candidate_scores`** (numeric dict) and, as a fallback if scores are missing,
  `winning_concept_id`; also `source_text_span` for rarity weighting. Top-K normalized, log-damped,
  aggregated into `weights[cid]`. **It never reads `rule_trace`, `winning_reason_codes`, or
  `audit`.**
- `hesperia/extensions/triz/contradiction_feedback.py:23-24` — reads only `winning_concept_id`.
- `core/engine/projection/dlcr_public.py:16-22` — reads only `winning_concept_id`.
- `rule_trace`/`winning_reason_codes`/`candidates_detail` are consumed only by human-facing/audit
  tooling — `tools/export_tfp_ru_reasoning_bundle.py:352` (`s.get("winning_reason_codes")`,
  labeled "причины"/"reasons" for a report) — and by schema/presence tests
  (`tests/lexical_concept/test_resolver.py`, `tests/lexical_concept/test_resolver_output_schema.py`).
  No programmatic downstream logic branches on *which rule won*.

**Conclusion**: nothing downstream assumes the winning score came from a static/authored-only
source. Everything that matters programmatically (hex weighting, attribution) consumes the **final
numeric magnitude only**, agnostic to its internal composition. Adding a second, corpus-derived
contributor to that magnitude is fully absorbed by the existing consumer contract as long as it
stays inside `candidate_scores`' numeric shape.

## 3. Does wiring `coherence_empirical_weight` touch `core/propagation/` or `core/hexmap/`?

No evidence found that it needs to. `project_concepts_to_hex` (`core/hexmap/projection.py:10-18`)
takes only `concept_weights: dict[str, float]` — a flat `concept_id → weight` map with no resolver
provenance fields at all. `core/propagation/` grep for
`winning_concept_id`/`resolve_hit`/`candidate_scores`/`rule_trace` returned **zero hits** —
propagation's modules (`invariant_enforcer.py`, `gamma_guard.py`, `theta_gate.py`,
`shadow_layer.py`, etc.) never see anything about *how* a concept was resolved, only aggregated
hex/family/area state built from the final weight map.

This confirms CHI-015 §0's structural claim in code: D's blast radius, wired as an addend inside
`coherence_from_related`'s contribution to `score_candidate`, stays entirely inside
`core/resolver/`. Hexmap/propagation only ever see the resulting scalar weight per `concept_id`,
never the scoring rule that produced it.

## 4. Existing calibration/config surface for resolver weights

Two relevant surfaces exist, and neither is `coherence_from_related`-specific yet:

- `assets/config/engine_constants.json`, `resolver` node: `weight_relevance=0.45`,
  `weight_specificity=0.35`, `weight_locality=0.2`, `context_overlap_norm=5.0`,
  `specificity_norm=10.0`, `priority_norm=100.0` — read via `get_constant("resolver.<key>",
  default)` in `core/resolver/score_rules.py:33-42`. `weight_locality` governs the *whole*
  `local_signal` bundle (context overlap + coherence + fixed locality term), not `coherence_boost`
  in isolation.
- `assets/data/engine_dynamics_v060/dlcr_policy.yaml:7-9` already has a **precedent knob for
  exactly this class of feature**: `sequential_association_weight: 0.0  # 0 = off (keeps gold
  corpora stable); raise for PO-23 experiments`, plus `cooc_window: 4`. This feeds `resolve_hit`'s
  pre-existing `association_boost: dict[str, float] | None` parameter (`core/resolver/resolver.py:21,27-29,43,51`),
  described in its own docstring as "adds bounded prior mass from co-occurrence layer (PO-23)."

**Important scope correction**: this existing `association_boost`/PO-23 mechanism is **not** a
corpus-level Dict D — it's a same-document, in-request signal. In `pipeline.py:685-694`, `ab` is
built from `recent_winners` (the last 3 resolver winners *within the current text being
analyzed*), giving a flat `seq_w` bump if a candidate wasn't among the last 3 winners. Separately,
`pair_counts_from_canonical`/`top_pairs` (`pipeline.py:669-670`, `core/lexical/cooccurrence.py`)
computes token-level co-occurrence over the current text, but it is **explicitly discarded and
unused**: `pipeline.py:823` — `_ = (pins, top_pairs, cross_fam, ...)`. So today's codebase has
scaffolding for "a co-occurrence signal boosts resolver scores" but no persistent, corpus-level,
cross-document artifact — exactly the gap CHI-015 names.

Two structurally distinct places D's weight could land, both requiring **new keys**, not reuse of
existing ones:

1. Extend the `association_boost`-style additive path (parallel to `sequential_association_weight`)
   with a Dict D-fed boost — closest existing precedent, same clamp discipline
   (`max(0.0, min(1.0, boost))` then `saturate`, `core/resolver/resolver.py:43,51`).
2. Add a dedicated `coherence_empirical_weight` inside `coherence_from_related`/`score_candidate`
   itself, multiplying D's NPMI/G² contribution before summing into `local_signal` — this is what
   CHI-015 §8 names, and it does **not** exist today; `resolver.weight_locality` is the closest
   thing and it's too coarse (governs 3 unrelated terms at once).

Either path is a **new `engine_constants.json`/`dlcr_policy.yaml` key**, not an extension of an
already-parametrized coherence-specific surface.

## 5. Invariant checks

`core/propagation/invariant_enforcer.py:1-193` operates only on the **final 6-key engine output
contract** (`governance, loopability, tension_energy, obstacle_score, dominant_family,
dominant_area` — `REQUIRED_OUTPUT_KEYS`, `:31-34`) plus static geometry/bijection checks
(`AREAS=12`, `FAMILIES_PER_AREA=24`, hex/side bounds) and `check_family_in_area` structural
membership (`AREA_FAMILY_MAP`, `:174-178`, matching `genesis_taxonomy_provenance.md:73-75`'s
description). `tests/test_invariant.py` mirrors exactly that surface (geometry, bijection,
output-contract, clamp tests) — **no per-scoring-component invariant tests exist** for resolver
internals.

Comparison point requested (`base_weight`/`saturation_k`/`cap`): these live in a *different*
module, `hesperia/engine/concept_dictionary/validator.py:14-70` (`validate_cd_row`) — a separate
TFP/CD activation system, not the resolver. Its discipline there is **type-only**
(`float(act[k])  # raises if bad`, `:27-30`) for `base_weight/cap/saturation_k/threshold`, with one
genuinely *bounded* check: `effects.amplifies/inhibits` factors must be in `[0, 2]` (`:60-62`). So
even the closest existing precedent for "numeric config bound checking" is mostly type-validation,
with range-checking done ad hoc per field, not generically.

For the resolver's own math specifically: `clamp01` (`core/dynamics/numeric.py:37-40`) **already
generically guards NaN/Inf/out-of-range** for any value that passes through it — `if
math.isnan(value) or math.isinf(value): return 0.0`. Every path that would carry a D-derived score
into `resolve_hit`'s final `activation` terminates in `saturate()`/`clamp01()`
(`score_rules.py:18-19,43-47`; `resolver.py:51`), so **a NaN or unbounded NPMI value reaching the
in-request scoring math is already absorbed by existing machinery**, no new invariant code required
there.

What genuinely **would** need a new check (not covered by anything existing): validating the *D
artifact itself* at load time — schema shape of `dict_d_*.jsonl` rows (`concept_id_a/concept_id_b`
referencing real current B concepts, no duplicate `(a,b)`/`(b,a)`, `npmi` actually within `[-1,1]`
in the file, `cooc_count >= 5` floor honored, `g2` non-negative). No such file-level validator
exists yet for a fourth dict — `dict_b.schema.json` is the nearest structural precedent (JSON
Schema for a dict file) but there is no equivalent for D, and `validate_cd_row`'s pattern
(raise-on-bad-type, MVP-scoped bounds) is the nearest code-level precedent for what a D-row
validator would look like.

## 6. Other structural dependencies on `related_concept_ids` being single-source

Repo-wide grep (non-test) for `related_concept_ids` returns exactly two hits:

- `core/resolver/context.py:35` — the resolver consumer described above.
- `tools/expand_dict_b_tfp_controlled.py:382,387,446` — a Dict B **build/expansion tool** that
  writes `related_concept_ids` (dedupes/truncates to 16 entries), not a runtime consumer.

No other module iterates, serializes, or assumes exclusivity of `related_concept_ids` as *the
only* relation signal. A second relation source (D) would not need to be merged into the list
itself — it's consumed at a different point (the resolver's scoring, not the field's storage),
which is consistent with CHI-015 §7's explicit "never auto-merges into B" rule.

---

## (a) D's real direct/indirect relations to A/B/C

Confirmed, not just asserted by the doc: in the actual code, D has **no direct edge** to A or C.
The only real ingestion point for anything D-shaped is `resolve_hit`'s scoring path
(`core/resolver/resolver.py`), which touches B (`concept_index`, `related_concept_ids`) and A only
indirectly (A supplied the `LexicalHit`/`candidate_concept_ids` that got resolved in the first
place — D never reads A itself). Concretely:

- **A→B edge D would reweight**: `coherence_from_related`'s count-based `0.15 * |related ∩
  siblings|` term, folded into `local_signal` — exactly where CHI-015 §8 says to add
  `coherence_empirical_weight`.
- **B→C edge D would reweight**: BAC recovery prioritization (`lexicon_resolver.md`'s
  `stabilize_calibration_v052_4.py` recovery loop) — outside this repo's currently-searched code
  paths beyond the doc's own description; not independently re-verified beyond what
  `lexicon_resolver.md:280-295` documents (BAC path exists and is B-first/A-marker-driven; I did
  not trace `stabilize_calibration_v052_4.py` itself in this pass).

CHI-015 §0's claim is confirmed by the actual resolver code: D genuinely has no A-facing or
C-facing hook of its own — every plausible integration point runs *through* B's concept_index /
`related_concept_ids` machinery.

One correction worth flagging: CHI-015 §0 casually calls B "288 labeled dots." In the actual repo,
288 is the **family×area slot count** (12 areas × 24 families, `hits_288 = [0.0]*288` in
`pipeline.py:757`, `_family_slot_index`), not a Dict B concept count — the current core/default
`dict_b_seed.jsonl` has **11 rows** (`assets/data/engine_dynamics_v060/dict_b/dict_b_seed.jsonl`),
and the "288-row core Dict B seed" the task context mentions as not-yet-existing is consistent with
that — no current or planned artifact where B actually has 288 concept rows was found; treat "288"
in CHI-015 as shorthand for the family/area slot geometry, not a concept-count fact.

## (b) Concrete outcomes / programmable features D would unlock

- **Corpus-grounded disambiguation on genuinely ambiguous candidate sets.** Today
  `coherence_from_related` only rewards a candidate if *another candidate proposed by the same
  LexicalHit* happens to be hand-listed in its `related_concept_ids` (`context.py:35-39`) — a
  narrow, same-span-only signal. With D wired as `coherence_empirical_weight *
  npmi_or_g2(candidate, other_active_concepts)`, disambiguation could draw on empirically-observed
  association across the *whole* resolved document (not just co-proposed candidates in one hit),
  closing real gaps where B's hand-authored graph is sparse (documented as a real risk in
  `lexicon_resolver.md`'s ACB/BAC coverage discussion).
- **Tie-break correction — but only where CHI-015 already scopes it correctly.** The fixed
  tie-break (`tiebreaks.py:8-24`: specificity rank desc, then lexical concept-ID order) only fires
  when `top_score` is *exactly equal* across candidates (`resolver.py:69-76`). Since D would enter
  *before* the tie-break, as an addend inside `coherence_boost`/`local_signal`, its practical
  effect is to **make exact-score ties less likely in the first place** (more candidates get
  separated by real evidence), rather than literally replacing the tie-break rule itself. CHI-015
  doesn't claim the tie-break logic changes, and the code confirms it wouldn't — D changes the
  scores that feed into tie detection, not the tie-break function.
- **A real corpus-drift/coverage metric** (§8's "% of D-observed pairs also present in B's
  authored graph") is directly buildable off `agreement_with_b` with no resolver changes at all —
  a pure offline analysis over D once it exists, independent of whether D is ever wired into live
  scoring.
- **BAC-recovery prioritization** becomes evidence-driven rather than purely
  definitional-vocabulary-driven (today: `_phrase_from_lexicals` synthesizes recovery phrases from
  a concept's *own* prior lexical markers/label only, per `lexicon_resolver.md:280-295` — no
  cross-concept signal at all today).

## (c) Backward adjustments to core

**Required before D can be wired (nothing else works without this):**

1. **Stage 2 must exist.** D counts co-occurrence over *resolved* `concept_id` sequences (CHI-015
   §2-3); `core/engine/lexical_concept/pipeline.py`'s `_analyze_internal` is the only resolver
   call site that runs over full documents, and today's core/default Dict A is confirmed synthetic
   placeholder data with "zero real vocabulary" (`docs/foundations/genesis_taxonomy_provenance.md:76`).
   There is nothing to resolve yet — this is a hard, already-acknowledged (CHI-015 §2) prerequisite,
   not new information, but confirmed structurally: no ACB/attribution tooling for core exists
   (`genesis_taxonomy_provenance.md:83-85`: "No PDF/epub/docx extraction tooling and no
   term→family attribution tooling exist anywhere in the repo today").
2. **A new config key**, since none currently isolates coherence's contribution — either extend
   `dlcr_policy.yaml`'s `sequential_association_weight` pattern (parallel `association_boost`
   entry sourced from D instead of same-document recency) or add
   `resolver.coherence_empirical_weight` to `assets/config/engine_constants.json` and thread it
   through `core/resolver/context.py`/`score_rules.py`. Confirmed no existing key covers this
   (`engine_constants.json`'s `resolver` node has exactly 6 keys, none coherence-specific — §4
   above).
3. **A D-artifact loader + row validator**, analogous to
   `hesperia/engine/concept_dictionary/validator.py`'s `validate_cd_row` or
   `assets/schemas/lexical_concept/dict_b.schema.json` — nothing today parses a 4th dict file or
   validates `(concept_id_a, concept_id_b, cooc_count, npmi, g2, agreement_with_b)` rows. This is
   new code, not an extension of an existing generic loader (`_merge_dict_a`/`_merge_dict_b` in
   `pipeline.py:135-189` are shape-specific to A/B rows).

**Optional/future (would improve it, not blocking):**

- Wiring D into hexmap/propagation is **not needed and not recommended** — confirmed in §3 that
  both layers are already fully blind to resolver provenance, consuming only the final
  `concept_id → weight` map (`project_concepts_to_hex`, `core/hexmap/projection.py:10-18`). No
  adjustment there is required by D's design, and CHI-015 §7's "never merge into B" rule is
  consistent with keeping it that way.
- Turning the currently-dead `pair_counts_from_canonical`/`top_pairs` computation
  (`pipeline.py:669-670,823`) into a live signal is unrelated to D specifically (it's
  same-document token co-occurrence, not corpus-level concept co-occurrence) but is worth noting
  as an existing unused piece of related infrastructure a future implementer might be tempted to
  conflate with D — they are not the same mechanism.
- A dedicated numeric-bounds test suite for resolver scoring components (paralleling
  `tests/test_invariant.py`'s output-contract tests) would be a genuine improvement given §5's
  finding that no such component-level invariant tests exist today — but `clamp01`'s existing
  NaN/Inf guard already makes this a robustness *nice-to-have*, not a blocker, since malformed
  values can't propagate past the final `saturate()` call regardless.

**Could not verify**: `projects/ops-method/scripts/it_cta_relation_invent.py`, cited in CHI-015
§1/§7 as the "review_status='pending'" precedent — this path does not exist inside
`/data/hesperia/hesperia` (searched, zero hits); it's a different repo (`ops-method`, in the brain
repo `/data/altitudine/CC_.com/`) outside this task's scope, so it could not be confirmed from
inside a Hesperia-scoped research pass. Read directly and confirmed separately, in the brain repo,
earlier in the same design conversation — not a gap, just a note on which repo each claim in this
file was checked against.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-09-04 | preserved research snapshot, pre-Dict-D-creation, grounding CHI-015 §8a against live resolver/pipeline code
