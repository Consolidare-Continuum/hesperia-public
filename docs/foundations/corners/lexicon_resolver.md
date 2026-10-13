# Corner: Lexicon and Deterministic Resolver (Dict A / Dict B, `lexicon/`, `core/lexical/`, `core/resolver/`)

## Why this corner exists at all

This is the load-bearing foundation under every other corner in the system,
because it is the only place where Hesperia touches raw natural language. If
this layer is non-deterministic or unauditable, nothing built on top of it —
hex projection, propagation, shadow correction, logic rules, guards — can be
trusted, because they would all be amplifying noise from an unstable input.

The founding design memo (`docs/foundations/theory_description.txt`) states the problem
precisely: the hard part was never designing families or areas (those can be
specified by hand); the hard part is deterministically converting messy
natural language into stable concept evidence. An LLM can do this conversion
fluently but not repeatably, and Hesperia's entire reason to exist is that
repeatability is a hard requirement, not a nice-to-have.

## What would break without it

Without a controlled lexicon and an explicit resolver, "family activation"
would be decided by whichever heuristic happens to run first on raw tokens —
the classic lexicon-classifier failure mode where everything collapses into
"some category" with no way to tell whether two hits are the same kind of
evidence or coincidentally landed in the same bucket. Worse, any ambiguity at
the word level would leak straight into family/area activation ("family
drift"), and every downstream invariant (Sigma's shape checks, Gamma's
determinism checks) would still pass syntactically while the *semantics* were
silently garbage. Determinism at the data-structure level is cheap; the
expensive, foundational part is determinism at the *meaning* level, and that
is what this corner is responsible for.

## The Dict A / Dict B split

- **Dict A** (`assets/lexicon/curated/DICT_A_SURFACE_MAP_*`, `A_CORE_STAR_MAP_*`) is
  the surface-evidence layer: words, stems, phrases, transcript variants,
  colloquial forms. Dict A does not classify — it *proposes* candidates.
- **Dict B** (`assets/lexicon/frozen/dict_b_v040_from_a_v0413.json`, `B0_TOKEN_TO_FAMILY`,
  `B1_SIDE_TO_FAMILY`) is the concept/family layer: semantic units, hierarchy,
  family and area membership, disambiguation clues. Dict B does not guess
  words — it receives resolved evidence.

This split exists so that lexical drift (new slang, new transcription
variants) can be absorbed by editing Dict A without ever touching the
semantic commitments in Dict B, and conversely so that re-deriving Dict B's
generation rules (`B0_TOKEN_TO_FAMILY_..._from_A_...json` — the filename
itself encodes provenance: which Dict A version produced this Dict B) is
always traceable to an exact frozen input. The `.sha256` sidecar files next to
every frozen dictionary are not incidental — they are the mechanism by which
"this run used dict version X" becomes a falsifiable claim rather than an
assertion.

## Why the resolver is a separate module from the dictionaries

`core/resolver/` (resolver.py, tiebreaks.py, score_rules.py, context.py)
exists as its own concern because a dictionary by itself only proposes
*candidates* — multiple Dict A entries can match the same span, and multiple
Dict B concepts can be reachable from the same Dict A entry. Folding
disambiguation logic into the dictionary data would make the dictionary
non-declarative (you couldn't update entries without auditing scoring side
effects) and would make the scoring logic untestable independent of dictionary
content. Separating them lets the dictionaries stay pure data (editable,
diffable, hashable) while the resolver stays pure logic (testable against
fixed inputs regardless of dictionary version).

The resolver's required behavior — phrase-first matching, longest-span
priority, exact-match-over-lemma-over-stem ordering, context-overlap scoring,
specificity bias on ties, and a fixed final tie-break — is not an
implementation detail; it is the only thing standing between "deterministic
system" and "system that happens to be deterministic on the day a particular
dictionary file doesn't have any ambiguous entries." The audit requirement
(per span: source text, normalized span, candidate concepts, winning concept,
why it won) is what makes Sigma/Gamma-style invariant checking meaningful one
layer up — without per-span justification, a passing invariant check could
still be certifying a lucky coincidence rather than a sound resolution.

## Why normalization (`core/lexical/normalization.py`, `text_lang.py`) is upstream of everything

Normalization (case-folding, punctuation policy, tokenization, lemmatization)
has to be frozen and versioned *before* lexical matching, because any
non-determinism introduced here (e.g. an unpinned tokenizer library) silently
re-derives the entire resolved-concept trace on every dependency bump, even
though "nothing about the lexicon changed." This is why the theory memo
insists determinism must mean "one raw_text → one output under fixed
versioned resources," not just "no machine learning involved" — a frozen
rule-based normalizer can still be non-deterministic in practice if its
toolchain version isn't pinned.

## How Dict B catches evidence from Dict A — three different mechanisms, not one

"Dict B catches from Dict A" is not a single, uniform relationship — the
codebase contains three structurally different catch mechanisms, evolved
across different eras, and a fourth case where the dependency direction is
flipped entirely. Conflating them would misstate how any one of them actually
works.

### 1. Build-time collapse: B0/B1 as a coarsened projection of A (original v0.4.1.x lineage)

In the frozen `assets/lexicon/frozen/` lineage, Dict A's entries point at a
**side_id** — one of `TOTAL_SIDES = 432,000` addressable leaves
(`core/topology/invariant_catalog.py`: `SIDES_PER_FAMILY = 1,500`). Dict B's
token-level table in this lineage — `B0_TOKEN_TO_FAMILY_v0_4_1_4_from_A_v0_4_1_3.json`
(the filename's `_from_A_v0_4_1_3` suffix is the provenance claim, in the
same spirit as the `.sha256` sidecars) and the equivalently-shaped
`dict_b_v040_from_a_v0413.json` — stores only a coarser **family_id**
integer per token. The relationship between the two is pure integer
division: `family = side_id // SIDES_PER_FAMILY`, the exact same arithmetic
`core/attribution/attribution_shared.py`'s `load_dict_a` performs inline when
it reads a *legacy* Dict A entry (`fg = sid_int // SIDES_PER_FAMILY`). This
means B0 is not independently authored data — it is a **frozen cache of a
deterministic projection of A**, computed once so that a runtime call site
that only needs "which family" doesn't have to load the full side-level
Dict A table and repeat the division per lookup. `B1_SIDE_TO_FAMILY_v0_4_1_4.json`
is the same projection at finer grain: a frozen `side_id → family_id` table
rather than `token → family_id`, i.e. the division pre-computed for every
side rather than only for sides that happen to have a token pointing at
them. Both B0 and B1 "catch" A in the literal sense of taking A's
finer-grained claim and recording what it rounds down to, once, so later
readers can trust the cached answer instead of re-deriving it — the same
precompute-and-freeze discipline already established for calibration
artifacts.

### 2. Build-time expansion: the surface-alias field as a graded synonym ring around A's side

`assets/lexicon/curated/B_SURFACE_LEX_FIELD_v1.json` does the *opposite* of
collapsing — for a given `side_id`, it expands the single concept A's entry
points at into a **confidence-graded alias set**:

```
side_id → { canonical_lemma, aliases: [{alias, grade: "A"|"B"|"C"}, ...] }
```

`assets/lexicon/curated/FREEZE_RECORD_v1.json`'s own rules state the constraint
precisely: "Dict B: alias grades A/B/C only; `canonical_lemma` must appear as
grade A; no duplicate alias after normalization." Grade A is the exact
canonical surface form (always present, always identical to
`canonical_lemma`), grade B is a close synonym, grade C is a looser one —
e.g. `canonical_lemma: "justice"` with `{"fairness", "B"}` and
`{"justness", "C"}`. This is the same confidence-tiered synonym-ring idea as
a thesaurus's near-synonym grading (consistent with this dictionary's own
declared external sourcing from OEWN/WordNet-style resources in
[`activation_landing_loops.md`](activation_landing_loops.md)), applied here
to **catch and surround** one of Dict A's anchor points with the surface
vocabulary a human author or downstream matcher might reasonably substitute
for it — useful for query expansion or alias-aware re-matching, the reverse
direction of information flow from mechanism 1 above.

### 3. Run-time adjudication: the resolver catches a *candidate set*, not a single answer

The modern (v0.6.0-schema) path does not assume a Dict A match resolves to
exactly one Dict B concept. `core/lexical/matcher.py`'s `LexicalHit` carries
`candidate_concept_ids: list[str]` — a single surface match can legitimately
be lexical evidence for *several* Dict B concepts at once (the schema-level
Dict B record, `schemas/lexical_concept/dict_b.schema.json`, is a richer
object than the flat B0/B1 tables: `preferred_label`, `specificity_rank`,
`related_concept_ids`, `status` (`draft`/`active`/`deprecated`/`blocked`)).
`core/resolver/resolver.py`'s `resolve_hit` is where Dict B actually "catches"
that candidate set: for every candidate concept ID Dict A's entry proposed,
it scores the concept using **Dict-B-only information** the matcher never
saw — `label_token_overlap` (how much of the concept's own `preferred_label`
appears in the surrounding text window), `coherence_from_related` (whether
sibling candidates in the same hit are structurally related to this concept
via `related_concept_ids`), and `specificity_rank` — then picks the
highest-scoring candidate, with ties broken deterministically
(`break_tie`: specificity rank descending, then concept ID lexical order).
This is the literal audit trail `lexicon_resolver.md`'s opening section
promised ("per span: source text, normalized span, candidate concepts,
winning concept, why it won") — `resolve_hit`'s returned `rule_trace`,
`candidate_scores`, and `winning_reason_codes` are exactly that record. Here,
unlike mechanisms 1 and 2, Dict B is not a static cache or alias table — it
is an active participant in deciding which of Dict A's proposals survives.

### 4. The exception: in the TFP/Kernberg lineage, the dependency runs the other way

`tools/build_dict_b_from_tfp_sources.py` builds
`hesperia/ontology/dictB/concept_nodes.yaml` **directly from the Kernberg/TFP
theory source texts** (`1.md`, `2.md`, `3.pdf` via `pdftotext`), keyed off
`specs/families_structure_tfp.yaml`'s 240 families — with no Dict A input at
all. `tools/build_dict_a_markers.py` then runs in the *opposite* direction
from mechanisms 1–3 above: it extracts Dict A's lexical markers **from**
this already-built Dict B's `label`/`definition`/`example_context` fields
(documented in
[`activation_landing_loops.md`](activation_landing_loops.md)). So "how B
relates to A" has no single global answer — it depends on which dictionary
pack is in play: the original frozen lineage has **A first, B catches/
collapses/expands from A**; the TFP-Kernberg lineage has **B first
(from theory text), A extracted from B**. Anyone reading a `*_from_A_*` or
`*_from_*_sources*` filename should treat that suffix as the authoritative
answer for *that specific artifact*, not assume a fixed system-wide
direction — the naming convention exists precisely so this doesn't have to
be inferred.

## Dict C: phrase-level synthesis layer — why it exists and how it is built from two directions

Dict C (`assets/calibration/dicts/<version>/dict_c.jsonl`) is a third
lexical layer that Dict A and Dict B alone cannot provide: a frozen table of
**multi-token phrase entries**, each linking one specific 2-3-word phrase to
exactly one Dict B concept, with higher evidentiary weight than a token-level
match. It is a calibration-time artifact, not a runtime one — it does not
appear in the `calibration_manifest` the runtime reads, and `_analyze_internal`
(`hesperia/engine/lexical_concept/pipeline.py`) does not load it; it is instead
the input from which the **`links.jsonl` provenance table** is built, which in
turn drives calibration evaluation coverage accounting.

### What Dict C looks like (the literal schema)

Every dict_c entry is structurally compatible with Dict A (same fields, same
matcher-ready format), but specialized:

```
entry_id:              C_CAL-NNNNN        (C_ prefix distinguishes from A's CAL-)
surface_form:          "<phrase text>"    (the phrase verbatim, as matched)
normalized_form:       same as surface_form
token_count:           2 or 3            (never 1 — single tokens belong to Dict A)
match_type:            exact_phrase      (always — no lemma/stem/pattern)
candidate_concept_ids: ["B_A10_F10_004"] (always exactly one Dict B concept ID)
priority:              99                (highest declared priority in the matcher)
status:                active
language:              ru | en | mixed
```

Current seal (`v0_6_0_clr_v052_5`): 24,000 Dict C rows; 10,155 Dict A rows in
the same bundle. The link table (`links.jsonl`) records each C entry as
`source_dict="C"`, `match_type="exact_phrase"`, `base_weight=0.9`, versus
Dict A's `source_dict="A"`, `match_type="exact_token"`, `base_weight=0.6`.

The 0.9 vs 0.6 contrast encodes the **phrase-specificity hypothesis**: a
multi-word exact-phrase match suppresses more candidate concepts than a
single-token match, so it deserves proportionally higher evidential weight.
This is the same reasoning behind phrase-level TF-IDF weighting in information
retrieval (Salton et al.'s vector space model, 1975; Manning & Schütze's
treatment of phrase indexing vs unigram indexing, 1999, §5). A single token
can plausibly activate many semantically adjacent concepts via weight
redistribution; a 3-token phrase in the target register almost always points
to one. Higher base_weight is the system's acknowledgement of reduced
conditional entropy at the phrase level: H(concept | phrase) < H(concept | token).

### Why Dict C is needed at all: the n-gram specificity gap

Dict A entries match individual tokens (one word, one lemma, one stem). Many
concept-diagnostic expressions in the target-domain corpus are inherently
multi-word: their disambiguation power lies in the collocational pattern, not
in any single constituent token. A two- or three-word phrase produces a
near-zero ambiguity LexicalHit that the resolver can confirm with minimal
context overlap scoring; a single token from the same phrase lands in Dict A
with far higher `candidate_concept_ids` entropy, requiring the resolver to
do significant additional work (label-token overlap, coherence-from-related,
specificity rank) before picking a winner. Dict C freezes the multi-token
patterns that are already unambiguous enough to be pre-decided — each one
maps to exactly one concept, `priority=99`, no resolver adjudication needed.
This is analogous to precompiling phrase-level lookup tables in computational
lexicography (Brill & Moore's error model, 2000, applied here not to
corrections but to pre-empting disambiguation cost).

### How Dict C is built: two construction paths (the ACB and BAC directions)

Dict C cannot be built from a single direction because it sits at the
intersection of two different information sources: the statistical distribution
of phrases in observed text (A's domain) and the structured semantic graph of
concept definitions (B's domain). The codebase implements both paths:

**A → C → B (corpus-driven, bottom-up — the ACB path).**
Start with raw corpus text → extract frequency-filtered n-grams
(`extract_corpus`, `min_freq=2`, n up to 5 tokens) — these are
**A-level surface candidates**, the same pool that would feed Dict A. LLM
normalization (`normalize_batch`, Task 2) canonicalizes forms; LLM concept
proposal (`propose_concepts`, Task 3) maps batches of normalized phrases to
draft Dict B concepts, constrained to prefer existing concept IDs (the catalog
of existing B concepts is passed in every prompt, capping `max_concepts=80` per
batch to prevent concept explosion). Anchoring (`anchor_drafts`, Task 4) binds
each draft to an existing Dict B record via `SequenceMatcher`-based
label/definition similarity (threshold `min_score=0.52`). The anchored rows
whose phrase is 2-3 tokens and whose anchor confidence passes become Dict C
entries. The information flow is **A** (n-gram pool) → **C** (anchored phrase) →
**B** (concept record): "what does the observed text distribution imply about
concept membership?" Epistemologically this is a bottom-up LLM-mediated
abduction — the LLM is used as a semantic distance estimator, offline, to
assign observed phrases to the nearest concept in B-space, with the result
frozen and hash-pinned before it enters the runtime.

**B → A → C (concept-driven, top-down, recovery path — the BAC path).**
When a concept present in a prior version's `links.jsonl` disappears from the
current version — lost because no n-gram in the latest corpus wave matched it
through the ACB pipeline — `stabilize_calibration_v052_4.py`'s recovery loop
reverses the direction. It starts from the **B concept's semantic identity**
(`preferred_label`, `family_ids`, `area_ids`) and retrieves that concept's
prior-version A-level lexical markers (from the earlier `links.jsonl`'s
`lexical` field). `_phrase_from_lexicals` then synthesizes a 2-3-token phrase
from those markers or from the preferred_label directly, preferring the
longest multi-token form available. The synthesized phrase is injected as a
new Dict C entry pointing back at the at-risk concept. The information flow is
**B** (concept identity, coverage at risk) → **A** (prior lexical markers as raw
material) → **C** (recovery phrase): "what surface phrase most directly
expresses this concept?" This is a top-down generation step, not a retrieval
step — the phrase is constructed from the concept's own definitional vocabulary,
not observed independently in new text.

Both paths produce the same Dict C format, but make epistemically different
claims. ACB entries are **inductive**: "this phrase was observed and assigned
to this concept with confidence ≥ 0.52." BAC entries are **deductive**:
"this concept requires surface coverage; this phrase expresses it." The
`entry_id` prefix `C_CAL-NNNNN` (sequentially assigned across versions) is
the only in-row provenance marker — which entries are ACB-origin vs
BAC-recovery can only be recovered from calibration tooling history, not from
the JSONL row itself.

The fact that both directions are necessary is a structural property of the
geometry of the lexical space: the corpus-observed n-gram distribution and
the concept-graph topology are not aligned (high-frequency phrases don't
uniformly cover all concepts; rare concepts need explicit phrases). Dict C
is the artifact that enforces alignment: `distinct_concepts_in_links` (the
calibration metric computed after each seal) is the scalar that measures how
well Dict C and Dict A together cover the full concept space — the closer
to |B| (total number of concepts), the more complete the phrase-level
synthesis.

### Language tagging and the script-detection apparatus

Dict C entries carry a `language` field (`ru`/`en`/`mixed`), populated by
`core.lexical.text_lang.retag_language_field_for_phrase` (Unicode script
block heuristic, not a language model). A dedicated retagging tool
(`tools/retag_calibration_dict_c_language.py`) and analysis tool
(`tools/analyze_dict_c_language_layer.py`) exist because early calibration
runs mis-tagged non-Latin-script normalized_form entries as `language="en"` —
the per-entry script detection was added post-hoc to an existing pipeline that
assumed a single-language corpus. `analyze_dict_c_language_layer.py`
quantifies the "Cyrillic script but `language_field=en`" mismatch count
before/after retag. This matters for routing and audit completeness: an entry
with non-Latin script tagged as `en` would misroute in any downstream logic
gated on `language` equality.

### What "Dict C synthesizes meaning of a concept" means exactly

Each Dict C entry is a **grounded lexical definition of a concept at phrase
resolution** — not a probabilistic surface pointer (Dict A's role) and not a
structured semantic record (Dict B's role). It answers a specific question:
"what is the shortest multi-token string that uniquely identifies this
concept in natural language, with conditional entropy H(concept | phrase) ≈ 0?"
That question requires knowing both the surface distribution (A's domain:
which phrases occur with what frequency in the observed text) and the
conceptual topology (B's domain: which concept does this phrase belong to,
given the full semantic graph). Building Dict C from a single direction leaves
a gap:
- ACB alone: phrase coverage tracks the corpus distribution but cannot
  guarantee that every concept in B has at least one phrase entry (sparse
  concepts are always under-represented in any n-gram frequency table)
- BAC alone: every concept gets a recovery phrase, but recovery phrases are
  derived from B's own definitional vocabulary, not from observed text, so
  they may not match real input distribution

Running both and maintaining the union as a sealed, versioned artifact is
what makes Dict C the synthesis layer: it is the minimum closed set of
phrases such that (a) every sufficiently-frequent corpus phrase with a
deterministic concept assignment is represented, and (b) every concept in
the active B vocabulary has at least one phrase-level entry. This
closed-set property is what the `distinct_concepts_in_links` metric tracks
— and it is why the calibration loop has both a convergence condition on
entropy and an explicit coverage recovery step before sealing.

**Why this does not currently run at inference:** `calibration_manifest`
(in `hesperia/engine/calibration_dict_paths.py`) exposes `dict_a.jsonl`,
`dict_b.jsonl`, `links.jsonl`, and `metrics.json` from the sealed bundle.
`dict_c.jsonl` is absent from this list. `_analyze_internal` in
`hesperia/engine/lexical_concept/pipeline.py` loads only `dict_a.jsonl`
(and `dict_b.jsonl`) from the calibration bundle — it does not add `dict_c.jsonl`
to the Dict A merge paths. The C-sourced phrases in `links.jsonl` are used
during calibration evaluation (concept coverage counts, entropy tracking,
`distinct_concepts_in_links` metrics) but do not currently participate in
live DLCR matching. The schema is runtime-compatible (`_merge_dict_a` accepts
any row with `normalized_form` + `candidate_concept_ids`), so loading dict_c
as an additional Dict A path is mechanically straightforward — it simply isn't
done yet in the default asset configuration.

## Exhaustive build/activation/landing treatment

For Dict A's exact build provenance (definitional extraction from Dict B
concept nodes; external lexicographic sourcing from OEWN/SCOWL/Wiktionary,
hash-pinned), the two independent matcher implementations actually running
in `core/lexical/` and `core/attribution/`, the literal `landing_source`
provenance mechanism (`explain_landing`, `exclude_landing_sources`), and an
explicit disambiguation between L2's structural loop count and the unrelated
trajectory `loopability` metric, see
[`activation_landing_loops.md`](activation_landing_loops.md) — written as
the activation-axis counterpart to `geometry_math_coupling.md` (shape) and
`physics_dynamics_coupling.md` (motion).

## Relationship to neighboring corners

- Feeds `core/hexmap/` and `sphere/topology/` (Layer 3): resolved concept IDs,
  not raw tokens, are what get projected into hex space (see
  `corners/hex_substrate.md`).
- Feeds `core/attribution/`: per-span provenance from the resolver is what
  attribution traces back to when a downstream metric needs to explain
  itself.
- Is the reason `specs/canon/families_master.txt`, `families_structure_tfp.yaml`,
  and `family_embedding_tfp.yaml` can exist as *fixed* structural definitions:
  because concept-to-family membership is resolved once, deterministically, at
  this layer, the family/area hierarchy above it never has to re-litigate
  ambiguity — it only has to aggregate.
