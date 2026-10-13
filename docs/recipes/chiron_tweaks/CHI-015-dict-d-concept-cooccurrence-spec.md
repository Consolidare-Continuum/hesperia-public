# CHI-015 — Dict D: concept×concept co-occurrence dictionary, spec at max reliability (not implemented)

> **Awareness (2026-09-04):** Stage1 seed is now **288** `AREA_FAMILY_MAP` rows in `v0_core_syzif_001/dict_b_seed.jsonl`. §0 historical “288 concepts” = slot geometry; live Dict B concept count tracks that seed after Stage2 offline seal. D artifact exists; weight inert.

> **Status reconciliation (CORE-D2-002, 2026-09-16):** “D artifact exists” means an
> inert 9,076-row mock artifact and partial loader/scoring scaffolding exist. It does
> **not** mean this specification has been implemented. The committed artifact was
> not built from paragraph-ordered resolved concept sequences, its tracked builder
> is absent, its sample/stability discipline is not operationalized, and no live
> pipeline caller loads it. The real implementation authority is
> `docs/specs/ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md` plus the
> `CORE-D2-000..099` gated program. Until that program reaches activation, the mock
> artifact is non-releasable and `resolver.coherence_empirical_weight` stays `0.0`.


## 0. Geometric framing — why D is not a peer of A/B/C (read before the spec below)

Preserved verbatim from the design conversation with the operator, 2026-09-04 — this is the actual
justification for §7's "never auto-merges into B" rule and for D's placements in §8 all being
*reweighting* uses rather than peer-artifact uses. Written before the spec, not after, because it
determines the spec's shape rather than decorating it.

**Where the geometry is right.** A/B/C genuinely are one plane. Every relationship among them so
far — A→B collapse, B→A alias expansion, the resolver's A→B adjudication, C's two build paths
(A→C→B and B→A→C) — is a translation between three flat, pre-existing point-sets. Nothing in that
triangle has interior. B is 288 labeled dots. A is a surface-form list. C is a phrase list. None of
them has distance between its own members — "concept 14 and concept 97" has no meaning inside B
alone; you can only ask "does some Dict A entry or Dict C phrase point at both." That is what
"logically plain" correctly names: relations only exist as edges between the sets, never within
one.

D breaks that, and "volumetric" is the right word for the kind of thing that breaks it — going
from a set of translation rules between three flat lists to a structure with real interior
(concept-to-concept distance, derived from evidence, living inside B itself) is a jump in kind, not
just a fourth item on a list.

**Where the geometry needs a correction — and it matters.** A tetrahedron needs D to have three
independent new edges — D–A, D–B, D–C, each carrying its own content, the way A–B, A–C, B–C each
do. D as spec'd doesn't have that. Every row in D is a `(concept_id, concept_id)` pair — it's B×B,
full stop. It never reads a surface form (A's territory) or a phrase (C's territory) directly. What
D actually does to A and C is indirect: it reweights the resolver's existing A→B edge
(`coherence_from_related`), and it reweights BAC's existing B→C edge (which concept gets recovery
priority). It has no edge of its own to A or C — it only ever bends edges that already existed.

So the more accurate picture: D isn't a fourth vertex lifted out of the plane. D is **curvature
injected into the B vertex itself** — B stops being a flat set of dimensionless points and becomes
its own internal graph, with real distance between its members — and that internal structure then
radiates outward along the two edges that already touch B, bending how A resolves onto it and how
C gets built to cover it. Not an apex with three new legs; depth added to one corner of the
existing triangle, propagating along the two edges that corner already had.

This isn't pedantry — it's the actual justification for something specified in §7 without fully
arguing for it there: why D must never be merged into B as a peer artifact, and must never be given
equal standing with A/B/C in a four-way combo. Geometrically, it isn't a peer of A/B/C — it's a
property of B, the way curvature is a property of a surface, not a fourth surface sitting next to
it. Merging D into B would be like trying to store a hex grid's curvature as a fourth flat family
list — a category error, not just a style choice.

**The precedent that makes this exact, not just poetic.** This isn't a new pattern for the house —
it's the identical move `corners/hex_substrate.md` already made one level up: families/areas are
coarse, flat, hand-specified bins; the 72k-cell hex layer is explicitly not decoration, it's "the
only layer with enough resolution to support locality and motion at all," precisely because flat
bins can't represent that two members of the same bin aren't identical, or that meaning can drift
between them. D is that same move applied to concepts instead of families: B's 288 concepts are
flat bins the same way families are; D is B's hex layer — the substrate that gives concepts real
neighborhood structure instead of just membership.

**What it would take to actually earn the tetrahedron.** If D also computed A×A (surface-form
co-occurrence, independent of resolution) or C×C (phrase co-occurrence), it would have genuine
independent edges not mediated through B, and the tetrahedron would be literal, not just evocative
— four real vertices, six real edges. That's not what's spec'd here, deliberately: an A×A or C×C
layer would be measuring surface statistics again, the exact thing A/C's LLM-mediated resolution
already exists to get past deterministically. The volume this spec wants is depth inside the
concept layer, not a fourth flat plane bolted on.

**Correction, post-research (2026-09-04, see §8a)**: §0 above (preserved verbatim, not edited) calls
B "288 labeled dots." That number is wrong in the way it's used there — verified against live code,
288 is the area×family *slot* geometry (12 areas × 24 families, `AREA_FAMILY_MAP`), not a Dict B
concept count. Core/default's actual `dict_b_seed.jsonl` today has **11 rows**. §0's geometric
argument itself is unaffected (B is still a flat, distanceless set of *whatever* size it is — the
argument doesn't depend on the count being 288), but every other place in this doc that says
"288 concepts" should be read as "the family/area slot geometry Stage 1's seed will be sized against,
real count TBD by Stage 1" — not a fact already established.

## 1. Task/goal

Design, not build: the concept×concept gap named in conversation with the operator (2026-09-04) —
Dict B's `related_concept_ids` are hand-authored graph edges; nothing in Dict A/B/C is
**empirically observed** from the resolved corpus. Dict D closes that gap. Same handoff posture as
CHI-014: this is §5b feature theorizing, proposed by Chiron, built by Felix/Gena after Grace
triage, not implemented here.

**Precedent, not invention**: `projects/ops-method/scripts/it_cta_relation_invent.py` already
solved a structurally identical problem in production — typed relation edges invented from corpus
evidence, always `review_status='pending'`, never auto-approved, lab-only until reviewed. D reuses
that discipline, not that code (different domain, different storage substrate — see §7).

## 2. Sequencing — hard prerequisite, not a preference

D cannot be built before Stage 2 (CHI-014/`STAGE-2-BUILD-PLAN.md`) lands. It is **Stage 9**, after
Stage 8's validation gate. Reason, stated precisely: D counts co-occurrence over **resolved
`concept_id` sequences**, not raw text — if it read raw corpus text independently of A/B/C, it
would be a second, disagreeing notion of "concept" competing with the resolver, not evidence about
the resolver's own concepts. There is nothing to count until Stage 2 produces a real resolved
corpus.

## 3. Input

Per book in `hesperia/modules/default/corpus/syzif/` (119 books, standing — see CHI-014 §2):
Stage 2's resolver output, walked in reading order — an ordered sequence of
`(concept_id, span_position)` tuples per book. Not n-grams, not raw phrases: resolved evidence
only.

## 4. Windowing — frozen and versioned, per the determinism requirement

"Show up near each other" is not self-defining (`docs/foundations/theory_description.txt`: "one
raw_text → one output under fixed versioned resources"). Three real options, with the honest
distinction the hex-substrate doc models (`corners/hex_substrate.md` §"Forced geometry vs.
engineered capacity") — which of these is a real constraint vs. an engineering choice:

| Window | Precision | Sparsity risk | Verdict |
|---|---|---|---|
| Fixed token span (e.g. ±50 tokens) | Low — crosses paragraph/sentence boundaries | Low | Rejected: cheap but semantically loose |
| Sentence-level | High | Very high — 288-family coarse catalog starves | Rejected: too sparse to reach most families |
| **Paragraph-level** | Medium-high | Medium | **Default** — book prose has real paragraph structure (unlike TFP's session transcripts), the natural unit a human author uses to keep two ideas "in the same breath" |

This is an **engineering choice, not a forced one** — state it as such, the way 250-hexes-per-family
is a capacity budget and not geometry. Changing the window rule later is a new Dict D version
directory, never an edit to an existing one; the rule is part of the version identity, same as a
dict pack's version string.

## 5. Metric — the actual "max reliable" question

Raw PMI is a known trap here: `PMI(i,j) = log(P(i,j)/(P(i)P(j)))` is *maximized* by concepts that
co-occur once, purely because their marginals are tiny — flagged already in this conversation.
"Max reliable" means closing that trap properly, not just naming it:

1. **Minimum evidence floor** before a pair is scored at all — e.g. `cooc_count >= 5`. Engineering
   knob, tune after a real run, not before.
2. **NPMI (normalized PMI)**, bounded `[-1, 1]`, not raw PMI — makes weights comparable across
   concept pairs with wildly different base frequencies (a common family like GOOD-area concepts
   vs. a rare one).
3. **A significance test, not NPMI alone** — NPMI still doesn't distinguish "this co-occurs more
   than chance" from "this co-occurs more than chance, but only barely, on thin evidence." The
   standard, well-established fix for exactly this (used the same way `corners/corpus_wiring.md`
   grounds its TF-IDF/PMI stance in a named, citable method rather than an invented one) is a
   **log-likelihood ratio (G²) test** (Dunning 1993) — robust at low counts in a way raw PMI/NPMI
   is not, standard in corpus-linguistics collocation extraction. Every D row carries both an NPMI
   weight (magnitude) and a G² score (confidence the association isn't chance) — two different
   questions, not collapsed into one number.
4. **Deterministic, not LLM-mediated.** This is a real reliability advantage worth stating
   explicitly, not just a cost saving: D's core computation is pure counting + two well-established
   statistics — one raw_text → one output, zero LLM variance, more auditable than Dict A/C's
   LLM-mediated ACB path, not less. An LLM only optionally enters later, downstream, to help a
   *human* interpret a surfaced disagreement (§6) — never inside D's build itself.

## 6. Output schema

```
concept_id_a, concept_id_b   (canonically sorted pair — no duplicate (a,b)/(b,a) rows)
cooc_count                   (raw evidence count, paragraph-level)
npmi                         (bounded [-1,1])
g2                           (log-likelihood significance score)
window_rule                  (file-level metadata + sha256, not per-row — see §4)
source_books                 (which of the 119 books contributed evidence — provenance)
agreement_with_b             (enum: "agrees" | "novel" | "contradicts")
```

`agreement_with_b` is the disagreement-surfacing mechanism from the earlier design discussion, made
concrete: `agrees` = pair also present in B's authored `related_concept_ids`; `novel` = strong D
evidence, absent from B (a candidate B is missing); `contradicts` = B declares related, D shows
near-zero/negative association (a candidate the hand-authored taxonomy may have wrong). This field
is what makes D useful beyond its own numbers — see §8.

Filename convention matches the existing provenance discipline (`lexicon_resolver.md`):
`dict_d_from_B_<version>_corpus_<snapshot>_win_paragraph.jsonl` + `.sha256` sidecar.

## 7. Reliability discipline — the ops-method precedent, applied

- **Never auto-merges into B.** D is a separate, versioned artifact consumed as an *additional*
  scoring signal by the resolver's `coherence_from_related` — not a silent rewrite of authored
  `related_concept_ids`. Same "confidence-tiered merge, never blind union" rule that governed every
  prior TFP dict merge.
  - `it_cta_relation_invent.py`'s `review_status='pending'` posture is the direct template: D's
    first version should ship with every row inert (informational, logged, not yet wired into the
    resolver's active scoring) until a human/Colombo review pass confirms a sample makes sense —
    same "propose, never auto-approve" discipline, adapted from a live-DB `review_status` column
    to a versioned-file "not yet consumed by the resolver" gate, because D's storage substrate is
    flat JSONL, not a mutable Postgres table (real difference from ops-method, named plainly, not
    glossed over).
- **Sample-validate, never trust the summary stat.** Pull N random high-NPMI `novel` pairs and N
  random `contradicts` pairs, human-check against real source-text excerpts that the relation (or
  its absence) actually makes sense. Same discipline that caught real bugs three separate times in
  the OCR cleanup history — a smaller/lazier check missed each one.
- **Stability check across corpus perturbation.** Does the graph change wildly if one book is
  dropped or the corpus grows by a few titles? A relation table that flips on a single book isn't
  evidence, it's overfitting to one author's vocabulary. Analogous to the "dominant-area stability"
  system-behavior metric already used for release gates elsewhere in this repo.
- **Lab/dev-only**, same as every other Stage 9+ artifact — dev repo (`igareosh/hesperia`) only
  until Stage 8-equivalent validation, never built against prod.

## 8. Placements and combinations — where D gets used once it exists

- **Resolver scoring input.** Feed `agrees`/`novel` pairs' NPMI+G² weights into
  `coherence_from_related` as a second, independent signal alongside B's authored graph, gated by
  its own calibration weight (new knob — e.g. `coherence_empirical_weight`). This is a genuine
  `docs/recipes/params_combo/PC-*` candidate the moment D exists: any future combo tuning resolver
  weights now has this knob to combine with existing ones (context-overlap weight, specificity
  bias). **Never** a replacement for the authored weight, only an addition.
- **Colombo's wiki-status review queue.** `contradicts` rows are exactly the kind of evidence
  CHIRON.md's "Ace of the Hesperia parameter/variable wiki" role exists to surface — Chiron reports
  status-change evidence, Colombo owns the content decision. Not a dictionary combo, but a real
  standing downstream consumer of D worth naming so it isn't missed.
- **BAC-recovery prioritization (Dict C, Stage 5).** If a B concept has zero Dict C coverage *and*
  D shows it co-occurring strongly with a well-covered neighbor, that's a concrete hint for where
  BAC recovery should look first, or which neighbor's vocabulary a recovery phrase might borrow
  register from. D doesn't do the recovery itself (still BAC's job) — it prioritizes and informs
  it. A real `PC-*` combo candidate: "D coverage-gap signal → BAC recovery ordering."
  candidate.
- **A new coverage/health metric.** Alongside `X/288` (A/C coverage) and `distinct_concepts_in_links`,
  add `% of D-observed pairs also present in B's authored graph` as a standing drift metric for
  future calibration passes — the same role `zero_lex_share` plays for TFP today.
- **Cross-family bridge signal for TRIZ-adjacent extensions** (`build_commercial_intelligence_bundle`,
  `family_conflict_density`) — D's empirically-observed cross-family/cross-area pairs are a
  potential new input to contradiction/innovation surfacing. Flagged, not scoped: this is
  extensions-adjacent territory, module-boundary question for Felix/Gena to confirm before wiring,
  same caution CHI-014 §3 already raised about core/TFP independence.
- **Explicit anti-combination**: D's JSONL is never merged directly into B's file, by convenience
  script or otherwise, even inside a params-combo recipe. Stated plainly here so a future recipe
  author isn't tempted to collapse the two artifacts for simplicity — that would erase the
  authored-vs-observed distinction that makes `agreement_with_b` meaningful at all.

## 8a. Verified against live resolver/pipeline code (2026-09-04)

Research pass against `/data/hesperia/hesperia`'s actual code, not just this doc's claims —
citations below are real, not illustrative. Full research report preserved verbatim as its own
artifact: [`research/DICT-D-PRE-CREATION-RESEARCH-2026-09-04.md`](../../../research/DICT-D-PRE-CREATION-RESEARCH-2026-09-04.md)
— this section is the digest, that file is the evidence trail.

**§0's structural claim holds in code, not just in the doc.** Traced every consumer of
`resolve_hit`'s output (`core/resolver/resolver.py:79-104`) across `core/engine/lexical_concept/
pipeline.py`, `core/hexmap/`, `core/propagation/`, `hesperia/extensions/triz/`. Hexmap
(`core/hexmap/projection.py:10-18`, `project_concepts_to_hex`) and propagation
(`core/propagation/invariant_enforcer.py`) consume only a flat `concept_id → weight` map — zero
hits repo-wide for resolver provenance (`winning_concept_id`, `candidate_scores`, `rule_trace`)
inside `core/propagation/`. **D's blast radius is confirmed to stay entirely inside
`core/resolver/`** — no hexmap or propagation changes are needed to wire it, and none are
recommended.

**`coherence_from_related`, exactly as it exists today** (`core/resolver/context.py:26-39`):
graded, not binary — `0.15 * len(related_concept_ids ∩ sibling_candidates_in_same_hit)` — folded
additively into `local_signal` alongside `context_overlap` and a fixed locality term, then
`clamp01`'d (`core/resolver/score_rules.py:35-39`, `core/dynamics/numeric.py:37-40` — which already
absorbs NaN/Inf to 0.0 generically, so a malformed D value can't corrupt live scoring even before
any new validation is written). No config key isolates `coherence_boost` alone today —
`resolver.weight_locality` in `assets/config/engine_constants.json` governs the whole three-term
bundle, too coarse to be "D's knob."

**A closer existing precedent than expected, currently dormant.** `assets/data/engine_dynamics_v060/
dlcr_policy.yaml:7-9` already has `sequential_association_weight: 0.0  # off`, feeding an
`association_boost` parameter `resolve_hit` already accepts (`resolver.py:21,27-29,43,51`,
docstring: "adds bounded prior mass from co-occurrence layer (PO-23)"). **Important scope
correction**: this is *same-document* recency (last 3 resolver winners in the current text being
analyzed, built in `pipeline.py:685-694`), not a corpus-level artifact — it is not D, but it is the
closest existing wiring pattern for "a co-occurrence signal boosts resolver scores," and D's
`coherence_empirical_weight` knob is more naturally added as a sibling to this pattern than as an
unrelated new mechanism. Separately: `pipeline.py:669-670,823` already computes
`pair_counts_from_canonical`/`top_pairs` (same-document token co-occurrence) and then **explicitly
discards it** (`_ = (pins, top_pairs, cross_fam, ...)`) — dead scaffolding, not D, but similar
enough in shape that a future implementer could wrongly conflate the two. Flagged here so they
don't.

**No invariant-check gap in live scoring; a real gap in artifact loading.**
`core/propagation/invariant_enforcer.py`/`tests/test_invariant.py` only check the final 6-key
engine output contract and static geometry (`AREAS=12`, bijection, `family_name in
AREA_FAMILY_MAP[area_name]`) — no per-scoring-component invariants exist, and none are needed for
D's live-scoring path specifically, since `clamp01`/`saturate()` already generically bound anything
flowing through the existing math. What genuinely doesn't exist yet: a **file-level loader +
row validator for a fourth dict** — nothing today parses/validates a `dict_d_*.jsonl` shape.
Nearest precedents to build from: `hesperia/engine/concept_dictionary/validator.py`'s
`validate_cd_row` (type-then-range-check pattern) and `assets/schemas/lexical_concept/
dict_b.schema.json` (JSON Schema precedent for a dict file) — no equivalent schema/validator exists
for D and would need to be written new, not extended.

**`related_concept_ids` has exactly two consumers repo-wide**: the resolver (read,
`context.py:35`) and `tools/expand_dict_b_tfp_controlled.py` (write, a B-build tool). No other
module assumes it's the only relation signal — confirms §7's "never merge into B" rule doesn't
conflict with anything else reading that field today.

**Tie-break precision**: D does not replace `tiebreaks.py`'s fixed tie-break logic (specificity
rank desc, then concept-ID lexical order) — that only fires on *exact* score equality
(`resolver.py:69-76`). D's real effect is upstream of that: by adding real evidence to
`local_signal`, it makes exact ties *less likely to occur in the first place*, not a different
resolution of ties that do occur. Worth being precise about since §8 below could be read either
way.

## 9. Config

N/A as a documented-parameter toggle today — but two concrete, code-grounded integration paths
exist for whoever builds this, not equally weighted:

1. **Preferred**: add `coherence_empirical_weight` alongside `resolver.weight_locality` in
   `assets/config/engine_constants.json`, threaded into `coherence_from_related`/`score_candidate`
   as D's own multiplier on the NPMI/G² contribution — matches CHI-015 §8's original placement
   exactly, isolated from the other three terms `weight_locality` currently bundles.
2. **Alternative**: extend the existing-but-dormant `sequential_association_weight`/
   `association_boost` pattern (`dlcr_policy.yaml:7-9`, `resolver.py:21-51`) with a D-fed sibling
   entry, reusing its clamp discipline (`max(0.0, min(1.0, boost))` then `saturate`). Closer to
   "reuse an existing mechanism," but that mechanism is *scoped* to same-document recency in its
   current form and would need to be generalized to accept a corpus-level lookup — real work either
   way, flagged for whoever builds it to pick, not decided here.

Either path is a new key, not an extension of an already-parametrized coherence-specific surface —
still out of Chiron's §5 direct-edit authority, same as CHI-014 §5.

## 10. Invocation

N/A — spec only. Sketch, not a commitment to exact function names: walk Stage 2's resolved
per-book concept sequences → paragraph-window co-occurrence counts → filter `cooc_count >= 5` →
compute NPMI + G² per surviving pair → tag `agreement_with_b` against current B's
`related_concept_ids` → write versioned `dict_d_*.jsonl` + sha256, rows inert (not yet consumed by
the resolver) pending sample review. Wiring into live scoring (once reviewed) means picking one of
§9's two integration paths and threading a new loader through `core/engine/lexical_concept/
pipeline.py`'s existing `_merge_dict_a`/`_merge_dict_b`-style load path (`pipeline.py:135-189`) —
those two functions are the nearest precedent for "load a versioned dict file into the pipeline,"
though D's row shape (concept×concept, not surface→concept) means a new function, not a shared one.

## 11. Expected output shape

Unknown until Stage 2 exists and a real resolved corpus can be counted — no target number claimed.
Report the real pair count, `novel`/`contradicts`/`agrees` split, and G²-significant fraction, not
a pre-committed size.

## 12. Validation evidence

None yet — pre-implementation spec, and prerequisite (Stage 2) isn't built either. Once built:
sample review per §7, stability check per §7, and — before the resolver ever consumes D's
weights live — the same `calibration_release_gate.py` + full pytest pre/post diff + live
`face=core` before/after call that gates every other dict change in this repo.

## 13. Rollback

New files only (new version directory) — nothing overwrites B or any existing sealed dict.
Rollback is "don't pin the new version" / "don't flip the resolver's `coherence_empirical_weight`
on," identical mechanism to every prior dict version swap.

## 14. Handoff

Per spec §5b: proposal, not implementation. Sequenced after CHI-014/Stage 2 lands — routed via
`inbox.md` → Grace triage → Felix/Gena, same path. Window-rule choice (§4), evidence floor (§5),
the extensions-adjacent TRIZ placement (§8), and the §9 integration-path choice are flagged for
whoever builds it to confirm, not resolved unilaterally here.

**Scope note on §1's precedent citation**: `it_cta_relation_invent.py` was read directly in the
brain repo (`projects/ops-method/scripts/`) earlier in the design conversation — a code-research
pass scoped to `/data/hesperia/hesperia` alone correctly could not find it there (different repo)
and could not independently re-verify it in that pass. Not a gap, just noting which repo each claim
in this doc was checked against.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-09-04 | Dict D spec at max reliability, precedent-grounded in ops-method's relation-invent discipline; §8a verified against live Hesperia resolver/pipeline code same day — not implemented, sequenced as Stage 9 after CHI-014/Stage 2
