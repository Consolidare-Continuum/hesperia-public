# Cross-cutting: Dict A — why it exists, how it is built, how/where it activates, where evidence lands, and the two unrelated "loop" concepts

This corner is the activation-axis counterpart to
[`geometry_math_coupling.md`](geometry_math_coupling.md) (shape) and
[`physics_dynamics_coupling.md`](physics_dynamics_coupling.md) (motion).
[`lexicon_resolver.md`](lexicon_resolver.md) already states *why* a
controlled lexicon and deterministic resolver must exist at all; this
document goes one level deeper into Dict A specifically — its build
provenance, the actual matching/attribution code (of which there are
multiple, era-specific implementations), the literal `landing` mechanism the
codebase names that way, and a precise accounting of "loop," which turns out
to name two mathematically unrelated quantities in different parts of the
system.

## Why Dict A exists (restated precisely, at the code level)

Dict A's job is narrower than "the dictionary" — per
`core/attribution/lexical_loader.py`'s docstring, "Spec 20: Dict A outputs
side_id only (no family_id/area_id)" and `validate_spec20_dict_a` *hard-fails*
on any Dict A entry containing a `family_id`/`area_id` key. This is a
load-bearing authority boundary, not a style preference: Dict A is permitted
to know "this surface form is evidence for side X," but is explicitly
forbidden from knowing or asserting "this surface form means family Y" —
that aggregation is reserved for the resolver/attribution layer one level up
(`B0_TOKEN_TO_FAMILY`, `aggregate_dominant`). If Dict A entries could name a
family directly, two structurally different claims — "this word is lexical
evidence for a concept" and "this word settles which family the whole text is
about" — would collapse into one ungoverned authority, which is exactly the
"word→family bypass" the codebase elsewhere builds an explicit guard to
exclude (`exclude_landing_sources={"A"}`, below).

## How Dict A is actually built

There is no single Dict A construction path; the codebase shows (at least)
two generations, both deterministic and both rule-based — no learned model
ever writes a Dict A entry directly:

**1. Definition-derived extraction (`tools/build_dict_a_markers.py`).** Dict A
markers are mechanically extracted from Dict B's own `concept_nodes.yaml`
(label, `definition`, `example_context` fields), not invented independently.
The algorithm is fully specified and reviewable:
- Tokenize Russian-language text (`tokenize_ru`: Cyrillic-aware regex,
  stopword-filtered against a fixed 60+ word list, `MIN_LEN=2`).
- Take the concept's own **label** tokens first (deduplicated), then
  `example_context`, then `definition` — i.e. the most concept-defining
  language is prioritized over incidental context language.
- Optionally re-rank the remainder by corpus unigram frequency
  (`load_corpus_word_counts`, `min_freq` threshold) so markers match the
  vocabulary of real domain text, not just the dictionary author's wording.
- Backfill from a fixed `AREA_EXTRA_MARKERS` table if a concept produces
  fewer than `MIN_MARKERS_PER_CONCEPT=5` markers organically — a documented
  floor ensuring no concept ships under-evidenced, at the cost of those floor
  markers being area-generic rather than concept-specific (an explicit,
  visible trade-off, not a silent one).

This is **extraction from an authored ontology**, the same general pattern as
building a controlled vocabulary from definitional text in classical
terminology/thesaurus construction (the same idea behind a domain thesaurus's
"use the defining text as the seed vocabulary," predating any ML
formalization).

**2. External-lexicographic sourcing, frozen with provenance
(`assets/lexicon/curated/FREEZE_RECORD_v1.json`).** A separate generation's Dict A
(`A_CORE_STAR_MAP_v1.json`) is sourced in part from named, dated external
lexical resources: `oewn` (Open English WordNet, version `v2023.1` —
Princeton WordNet's open-licensed continuation, Miller et al., 1990, the
founding lexical-semantic database whose synset/hypernym structure underlies
most controlled-vocabulary tooling since), `scowl` (Spell Checking Oriented
Word Lists, `2020.12.07` — a long-standing, size-graded English wordlist used
for exactly this kind of controlled-surface-form enumeration), and
`wiktionary` (`latest`). The freeze record pins a `repo_commit`, a
`frozen_at` date, and a `sha256` per artifact — the same hash-pinned
provenance discipline already established for Dict B in
`lexicon_resolver.md` ("`.sha256` sidecar files... are the mechanism by which
'this run used dict version X' becomes a falsifiable claim").

**3. Optional LLM-assisted calibration, strictly offline
(`openai_calibrate_dict_a.py`).** Per `corners/calibration.md`'s "why the
LLM-driven calibration scripts are offline tools, not runtime dependencies":
an LLM may be used to *propose or audit* candidate Dict A entries during
the build step, but the result is reviewed, frozen, and hash-pinned before it
ever reaches the runtime path — the same "calibration tooling is allowed to
use an LLM because its *output* (not the model call itself) is what enters
the frozen artifact" discipline applies here as it does to area/topology
calibration.

**4. Structural validation before use (`lexicon/validation/validate_dict_a.py`).**
Hard-fails (not warnings) on: wrong anchor count (must match
`FAMILY_SPEC_v0_6.json`'s 288 families exactly), per-token weight vectors
that don't sum to 1, negative weights, NaNs. Soft-warns (does not fail,
unless `--strict-strong-pct`) on a low "% strong tokens" rate. This is the
same hard-fail/soft-warn split already established for Sigma's structural
invariants versus advisory checks elsewhere — applied here at *build* time,
before Dict A is ever frozen, rather than at *run* time.

## How and where Dict A activates: there are two genuinely different matchers

The codebase contains two independently-evolved Dict A activation paths,
both deterministic, serving different eras/use cases:

**A. Phrase-first interval matcher (`core/lexical/matcher.py`).** Operates
on normalized text (`core/lexical/normalization.py`: NFKC, smart-quote
folding, casefold, whitespace collapse) and Dict A entries with explicit
`match_type` (`exact`/`phrase`/`lemma`/`stem`/`pattern`). For every entry it
finds every literal occurrence of its `normalized_form`, then resolves
overlapping candidate spans with a fixed sort key — **earliest start, then
longest span, then strongest `match_type`, then highest declared priority**
— greedily accepting non-overlapping winners in that order and routing every
loser to a `rejected` list rather than discarding it silently. This is a
**greedy interval-scheduling** algorithm: it is the same family of problem as
classical weighted interval scheduling (Kleinberg & Tardos' textbook
treatment traces this back to basic activity-selection results), but
Hesperia's version is deliberately **not** the optimal-weight dynamic-program
variant — it is a fixed-priority greedy pass, chosen because the *order* of
preference (longest-span-wins, exact-over-stem) needs to be auditable and
declared, not whatever an optimization happens to produce. `negative_patterns`
on an entry don't produce hits at all — they only carve out **blocked spans**
(`_collect_negative_blocks`) that suppress any other entry's match inside
them, a documented mechanism for "Ethan TFP RU negative layer" (excluding
known false-positive surface forms).

**B. Weighted full-vector attribution (`core/attribution/attribution.py`,
v0.6).** Rather than producing discrete spans, this path gives every token a
full 288-family weight vector. Each Dict A entry stores only its **top-k**
(`TOP_K=32`) strongest family associations explicitly; the remaining
`tail_mass = 1.0 - topk_sum` is redistributed across the other families
**proportional to a global `family_prior`**, not uniformly
(`tail_mass * prior[f] / sum_prior_excl`). This is the same structural move
as **Bayesian/Lidstone smoothing** in language modeling (assign unseen or
unlisted outcomes mass proportional to a prior rather than zero or a flat
constant) — applied here to "family associations a dictionary entry didn't
bother enumerating" rather than to unseen vocabulary. The sentence vector is
the per-token mean, re-normalized to sum to 1 (`_sentence_vector`); dominant
family/area is the `argmax` of that vector.

There is also a third, simpler **structural attribution** path
(`core/attribution/attribution_shared.py`) that does pure deterministic
Dict-A-exact / Dict-B-fallback lookup per token with no weight-vector
smoothing at all — the one that introduces explicit `landing_source`
vocabulary, covered next.

## "Landing": the literal term the codebase uses for resolution provenance

`core/attribution/attribution_shared.py` names this concept directly:
`explain_landing(token, dict_a, b0, b1_optional)` returns a `landing_source`
tag — `"A"` (direct Dict-A exact match), `"B0"` (Dict-B token→family
fallback), `"B1"` (Dict-B side→family table), or `"NONE"` (unresolved). Every
token in a text is tagged with exactly one landing source, and `attribute()`
accumulates `landing_counts` across the whole text — a per-run histogram of
*how* each piece of evidence was resolved, not just *what* it resolved to.

This is the precise mechanism behind the governance lever named in
`attribute()`'s own docstring (Ethan PO-11/PO-12): `exclude_landing_sources`
can be set to `{"A"}` to **forbid the word→family direct bypass** for a given
run, forcing every token that would have landed via Dict A to instead either
fall back to Dict B (`B0_fallback`, tracked as its own counter,
`b_fallback_after_a`) or land as `NONE` if Dict B doesn't cover it either.
This is the run-time enforcement of the "Dict A must not be the sole
authority for family membership" principle stated above — `landing_counts`
and `excluded_by_guard` give an auditable answer to "how much of this run's
evidence came from the fast/direct path versus the governed fallback path,"
which is exactly the kind of provenance question Sigma/Gamma invariants are
designed to make checkable rather than asserted.

`aggregate_dominant()` then turns the list of `(familyGlobal, altitude)`
landings into the per-family hit counts, mean altitude, and hit density that
`build_region_seed()` uses to compute `tau(side) = base_weight * hitDensity_F
* (1 - meanAltitude_F)` for every side in the dominant family — **this is
where lexical landing physically becomes the activation seed handed to the
hex substrate** (`corners/hex_substrate.md`), closing the loop between "a
word landed on a family" and "mass now exists at specific hex sides for
propagation to act on" (`physics_dynamics_coupling.md`'s diffusion machinery
takes over immediately after this point).

### Where in the pipeline this happens

`run_attribution_pipeline()` (both the v0.6 weighted-vector version in
`core/attribution/attribution.py` and the structural version in
`attribution_shared.py`) is the literal first computational stage of the
entire system: normalize → tokenize → attribute/land → aggregate dominant →
build region seed. This runs **before** `core/layers/layer_1.py`'s census —
L1 measures properties of the attribution this stage already produced; it
does not perform attribution itself. The "Activation" row of `00_INDEX.md`'s
plain-language pipeline table ("Raw text → controlled-lexicon matching (Dict
A) → disambiguated concept IDs (Dict B) → projection onto the hex substrate")
is this exact code path, named architecturally; this document is that same
claim traced to function names and formulas.

## "Loops": two unrelated quantities sharing one English word

Following the same disambiguation discipline already applied to "shadow" and
to the `layer_9` naming collision (`logic_guards.md`), it is worth stating
plainly that **"loop" names two mathematically unrelated things** in
Hesperia, and conflating them would be a real error:

**1. Structural loop count — graph circuit rank (`core/layers/layer_2.py`).**
After L2's BFS traversal from the dominant family, `LOOP_COUNT = max(0,
induced_edges − used_edges)` where `used_edges = TOTAL_REACHABLE_NODES − 1`
(the edge count of any spanning tree over the reached nodes) and
`induced_edges` counts every edge of the *original* adjacency graph with both
endpoints inside the visited set. This is exactly the classical
**circuit rank** (a.k.a. cyclomatic number) of a connected graph,
`μ = |E| − |V| + 1`, computed here as "edges actually present beyond what a
spanning tree would need" — a graph-theoretic invariant with origins in
Kirchhoff's circuit laws (1847, the original motivation for counting
independent cycles in a network) and formalized combinatorially soon after.
`LOOP_DENSITY = LOOP_COUNT / TOTAL_REACHABLE_NODES` then normalizes it by
traversal size, and both feed `GEOMETRIC_STABILITY_INDEX` as a multiplicative
penalty (`* (1 − LOOP_DENSITY)`) and `core/stability/stability_delta.py`'s
`PROPAGATION_LOOP` instability flag (`loop_density > 0.20 or loop_count >
2`). This loop concept is **purely structural** — it says nothing about time
or sequence, only "how many redundant/cyclical edges does the reached
subgraph contain beyond a tree."

**2. Trajectory loopability — temporal return/recurrence
(`core/result/contract.py`'s `compute_loopability`).** This is an entirely
different computation over a *sequence in time*, not a static subgraph:

```
return_frequency = clamp01(1 - transition_count / (segment_count - 1))
cycle_detection  = clamp01(1 - min(1, jump_distance / 24))
loopability = mean(return_frequency, cycle_detection, stability_window)
```

This measures whether a trajectory **keeps returning to states it has
already visited** rather than continuously exploring new ones — conceptually
adjacent to the recurrence-quantification idea in nonlinear dynamical-systems
analysis (Eckmann, Kantz & Ruelle's recurrence-plot framework, 1987: detect
how often a system's trajectory revisits a neighborhood of a prior state),
though Hesperia's three-term average is a much coarser, Hesperia-native
proxy, not a literal recurrence-plot computation. This `loopability` value
then feeds two further consumers with their own physics-flavored treatment:
`core/propagation/gamma_guard.py`'s stability penalty
(`loop_factor = 1 - loopability`, weighted 0.25 into `gammaPenalty` alongside
traversal-length and area-hop factors), and `core/propagation/shadow_layer.py`'s
`loop_hat = loopability * sqrt(mass)` — scaling the loop signal by the
**square root** of mass rather than mass linearly, the same
amplitude-scales-as-sqrt-of-intensity convention used throughout wave physics
(intensity ∝ amplitude², so amplitude ∝ √intensity) — applied here, as
elsewhere in this codebase's dynamics layer, as a borrowed *mathematical
shape* for "let a large quantity's influence grow sub-linearly," not a claim
that loopability is literally a wave amplitude.

**Why this distinction matters operationally:** L2's loop count can flag a
single text as structurally cyclical (its activation reached a tightly
interconnected subgraph) even on a *single* analysis with no history at all,
while `compute_loopability` is meaningless without a multi-step `trajectory`
object (`transition_count`, `segment_count`, `jump_distance`,
`stability_window`) — it literally cannot be computed from one isolated
result. Anyone reading "loop" in a Hesperia metric name has to check which of
these two unrelated computations produced it before drawing a conclusion
from it.

## Relationship to neighboring corners

- **[`lexicon_resolver.md`](lexicon_resolver.md)** — states the
  architectural *why* (Dict A proposes, Dict B/resolver decides); this
  document supplies the *how* — exact build provenance, exact matcher
  algorithms, and the literal `landing_source` vocabulary the resolver's
  audit trail is built from.
- **[`hex_substrate.md`](hex_substrate.md)** — `build_region_seed`'s
  `tau(side)` formula is the literal handoff point from this document's
  landing mechanism into that corner's hex-cell mass.
- **[`physics_dynamics_coupling.md`](physics_dynamics_coupling.md)** — once
  landing has produced seed mass at specific sides, that document's diffusion
  machinery (`diffuse_step`, `propagate_k_steps`) is what moves it from
  there; this document is upstream of all of it.
- **[`layers/L2_topology_traversal.md`](../layers/L2_topology_traversal.md)** —
  the authoritative source for `LOOP_COUNT`/`LOOP_DENSITY`'s role inside L2's
  25-variable census; this document adds the circuit-rank lineage and the
  explicit disambiguation against trajectory `loopability`.
- **[`calibration.md`](calibration.md)** — the sanctioned-offline-LLM-use
  rationale this document's Dict-A-build section relies on without repeating.
- **[`logic_guards.md`](logic_guards.md)** — the same naming-collision
  discipline (there: `layer_9`; here: `loop`) applied consistently across the
  documentation set.
