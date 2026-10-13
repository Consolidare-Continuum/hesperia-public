# CORE-D2 — Real Dict D program contract

**Status:** RATIFIED  
**Date:** 2026-09-16  
**Owner:** Ethan  
**Workflow task:** `CORE-D2-001`  
**Program register:** `CC_.com/operational/assignments/hesperia-dict-d2/CORE-D2-100-2026-REGISTER.md`  
**Parent gate:** `CORE-S2-LIVE-04`

## Decision

Build and activate a real core Dict D through the following mandatory sequence:

`candidate freeze → candidate evaluation → core pack gate → resolved corpus → deterministic Dict D → integrity → sample/stability → shadow calibration → atomic activation and rollback proof`

The existing mock Dict D is not eligible for activation. The current runtime weight remains:

```text
resolver.coherence_empirical_weight = 0.0
```

No task before `CORE-D2-090` may select a non-zero live value. No task before `CORE-D2-093` may activate a candidate pack.

## Architecture classification

Dict D is universal corpus-derived structure inside the core concept layer. It is a Class A/default calibration asset and scoring input. It does not redefine sealed geometry and does not enter a field-specific module.

The runtime blast radius is bounded to:

1. calibration-pack selection and validation;
2. lexical-concept resolver context;
3. final candidate scores and their trace.

Hex projection and propagation continue to consume final concept weights without learning Dict D internals.

## WBS boundary approval

**Approved boundary:** `CORE-D2-000..099`, ten gated waves of ten tasks.

**Included:**

- contracts and artifact authority;
- candidate A/B/C bundle freeze;
- candidate-aware evaluation;
- a core-native release gate;
- paragraph-ordered resolved-corpus export;
- deterministic pair counting, NPMI, and G²;
- Dict D schema, validator, provenance, and reproducibility;
- sampled relation review and graph stability;
- resolver-context wiring and shadow calibration;
- atomic activation, canary, rollback, and closure evidence.

**Excluded:**

- changing sealed hex geometry or propagation physics;
- merging Dict D rows into Dict B;
- automatic mutation of authored Dict B edges;
- field-specific corpus or prompt changes;
- TRIZ-adjacent use;
- promoting the old mock artifact;
- reopening `CORE-S2-000..299`;
- production activation outside W9.

**WBS Boundary:** APPROVED  
**Execution release:** W0 governance work only. W1 implementation remains blocked until W0 closes and Grace records the schedule/infra-duration disposition.

## Artifact states

| State | Meaning | May affect runtime |
|---|---|---|
| `quarantined` | Mock, contaminated, path-drifted, or failed artifact | No |
| `candidate` | Immutable bundle under construction or evaluation | No |
| `release_candidate` | Candidate that passed W1–W7 evidence gates | Shadow only |
| `active` | Atomically pinned manifest accepted under W9 | Yes |
| `last_known_good` | Previous active manifest with verified rollback hashes | Rollback target |

State promotion is monotonic through the gate sequence. A higher-state label cannot waive a failed lower gate. Rollback changes the active pointer to `last_known_good`; it does not rewrite either immutable bundle.

State names are machine labels and use the exact spellings above. A manifest
records both `state` and `supersedes`; directory names never serve as the state
authority. `release_candidate` is not active, and `last_known_good` always
identifies a previously active manifest rather than a reconstructed copy.

## Source and build contract

LIVE-06 outputs are candidate A/B inputs. They are not direct Dict D input.

Dict D input is a schema-valid, paragraph-ordered resolved-corpus export produced with:

- one immutable candidate bundle;
- stable source-book ordering and hashes;
- frozen paragraph segmentation;
- Dict D disabled to prevent self-influence;
- resolver/configuration identity recorded;
- winning concept and span positions preserved.

The builder consumes only that export. It must never recover concept evidence through raw-text substring matching.

Each pair is an unordered canonical pair `(concept_id_a, concept_id_b)` with `a < b`. Self-pairs and duplicate reversed pairs are invalid.

### Frozen paragraph segmentation

The source unit is a maximal run of non-empty UTF-8 text lines delimited by one
or more empty or whitespace-only lines. Before segmentation, line endings are
normalized from CRLF or CR to LF. No line wrapping, sentence splitting, heading
special-case, Unicode normalization, or whitespace reflow is allowed. Empty
units are discarded; remaining units retain internal line breaks and their
zero-based source ordinal.

`paragraph_id` is the SHA-256 of
`source_book_sha256 + NUL + decimal_ordinal + NUL + paragraph_text`.
`span_position` is a zero-based Unicode code-point offset in that exact
`paragraph_text`. Changing any segmentation rule creates a new build-rule
identity and therefore a new bundle; it cannot mutate an existing candidate.

## Statistical contract

The following terms have distinct meanings:

- `N`: count of segmented paragraphs presented to the resolver, including
  paragraphs with zero resolved concepts;
- `n_i`: count of paragraphs containing resolved concept `i` at least once;
- `n_ij`: count of paragraphs containing both resolved concepts `i` and `j`;
- `cooc_count`: `n_ij`;
- `npmi`: bounded association direction and magnitude in `[-1, 1]`;
- `g2`: unsigned, non-negative Dunning log-likelihood significance from a complete 2×2 contingency table;
- `source_books`: deterministic non-empty provenance for every emitted pair.

Repeated resolutions of one concept inside one paragraph count once. Every
unordered pair among the paragraph's distinct resolved concept IDs contributes
one event. Pair generation occurs after resolution and never from sibling
candidates or substring matches.

For `n_ij > 0`, `PMI = ln((n_ij * N) / (n_i * n_j))` and
`NPMI = PMI / -ln(n_ij / N)`. The perfect-co-occurrence limit
`n_ij = n_i = n_j = N` is exactly `1.0`. The contingency cells are
`[n_ij, n_i-n_ij; n_j-n_ij, N-n_i-n_j+n_ij]`; expected cells derive from row
and column marginals. `G² = 2 * Σ O * ln(O/E)` over non-zero observed cells,
with zero cells contributing zero. Negative cells, non-finite values, `N <= 0`,
or marginals outside `[0, N]` hard-fail.

The evidence floor is applied only after exact counts and marginals are complete. It may exclude rows from the released artifact but may not alter underlying totals.

Two clean builds from identical inputs must be byte-identical, including row order, metadata, and checksums.

## Agreement labels

- `agrees`: an observed emitted pair also exists in authored Dict B relations.
- `novel`: an observed emitted pair is absent from authored Dict B relations.
- `contradicts`: a review-only classification derived from a separate
  authored-edge audit; it is not an emitted runtime Dict D edge.

Absence of observed co-occurrence is not proof that an authored relation is false. `contradicts` is review evidence only and never directly contributes a negative runtime score.

Dict D remains a separate artifact. It must not be merged into Dict B or silently rewrite `related_concept_ids`.

Agreement is evaluated against the symmetric closure of Dict B's authored
`related_concept_ids`. Runtime Dict D rows therefore carry only `agrees` or
`novel`. Any `contradicts` finding lives in a separately hashed review artifact
with its frozen criterion and source excerpts. Dict C neither generates pair
events nor changes agreement labels. It may be used later to prioritize
vocabulary recovery, but that disposition is outside Dict D build and runtime
semantics.

## Bundle identity and mock quarantine

Bundle identity is the SHA-256 of a canonical manifest that pins exact A/B/C/D
artifact hashes, source-corpus hashes, resolver/configuration versions,
segmentation rule identity, statistical rule identity, and builder revision.
The manifest and referenced files are immutable after identity calculation.

The 2026-09-04 mock Dict D and any manifest that references it have state
`quarantined`, provenance `mock`, and release eligibility `false`. Mock bytes
may remain for historical tests, but may not be copied into a candidate,
release candidate, active pack, or last-known-good pack. Gates and runtime
selection hard-fail if a selected manifest is quarantined or has mock
provenance.

## Runtime context contract

Runtime loading occurs once per immutable calibration context, not once per lexical hit.

Resolution is deterministic and two-pass:

1. baseline pass: resolve the ordered paragraph with empirical weight `0.0`;
2. empirical pass: hold those baseline winners fixed as context and rescore each
   hit without allowing any empirical-pass winner to feed back into the same
   paragraph.

For a hit, paragraph context is the deduplicated set of baseline-winning
concept IDs from all other hits in that paragraph. Sibling candidates from the
same lexical hit are forbidden as context. The candidate itself and self-pairs
are excluded.

The unweighted empirical signal is
`max({max(0, npmi(candidate, context_id))} ∪ {0})`. This strongest-positive-edge
rule avoids paragraph-length inflation, makes negative NPMI review evidence
rather than a runtime penalty, and preserves authored/resolver scores as the
primary signal. Changing this aggregation or negative-edge policy creates a new
calibration-rule identity and requires a new candidate.

Both resolver call paths must receive the same context semantics. Traces must expose:

- matched empirical pair IDs;
- source Dict D version and hash;
- unweighted empirical signal;
- configured empirical weight;
- final empirical score contribution.

At weight `0.0`, candidate scores and winners must remain identical to the baseline even when shadow computation is enabled.

Dict D loading is manifest-pinned and fail-closed whenever a non-zero effective
weight or release gate is requested. Missing files, malformed rows, duplicate
or self pairs, non-finite values, bad hashes, unknown concept references, mock
provenance, and state/path drift are errors rather than skipped rows. Shadow
mode at effective weight `0.0` may report a load failure, but may not silently
claim a valid counterfactual.

## Class A module boundary

Universal empirical coherence is Class A default-calibration behavior. Pure
pair lookup and scoring functions belong under `core/resolver/`; lifecycle,
manifest selection, pipeline integration, and configuration belong under the
default module/calibration path. Build, corpus-export, review, and release-gate
tools remain outside runtime core.

No Dict D path may import field-specific corpus logic, prompts, concepts, or
branch behavior. Build tooling may depend on core interfaces; core must not
depend on build tooling. The runtime pipeline passes one immutable
paragraph-context object through both resolver call paths.

## Acceptance hierarchy

Acceptance is conjunctive. Every level must pass; no average score or degraded profile can compensate for a failed level.

### A0 — Authority and provenance

- Manifest identifies exact A/B/C/D artifacts, corpus snapshot, resolver configuration, and build rules.
- Mock, contaminated, missing-manifest, or candidate-path-drifted inputs fail closed.
- `exploratory_allow_degraded` is not release evidence.

### A1 — Structural integrity

- Schemas pass.
- Hashes match.
- Concept references exist in the same Dict B.
- Pairs are non-empty, distinct, canonical, and unique.
- NPMI, G², counts, and provenance satisfy their declared domains.

### A2 — Reproducibility

- Identical inputs produce byte-identical resolved exports.
- Identical exports produce byte-identical Dict D artifacts.
- Candidate evaluation serialization is deterministic.

### A3 — Candidate behavior

- Baseline and candidate use identical ordered inputs.
- Candidate evaluation actually loads candidate artifacts.
- Weight-zero output is a strict no-op.
- Frozen diff limits pass.

### A4 — Evidence quality

- Seeded stratified samples include source excerpts.
- Arithmetic and provenance sample failures equal zero.
- Human relation review meets the W7 threshold contract.
- Leave-one-book-out and corpus-growth stability meet thresholds frozen before the release build.

### A5 — Shadow calibration

- Real empirical pair hits occur in counterfactual traces.
- Controlled weight sweeps use frozen evaluation inputs.
- Ethan selects the smallest justified non-zero value.
- Gena confirms the runtime context semantics.

### A6 — Activation and recovery

- One manifest atomically selects A/B/C/D.
- Startup rejects missing or mismatched artifacts.
- Canary traces show real non-zero contributions.
- Fixed-input post-activation smoke passes.
- Rollback restores the prior manifest, runtime metadata, and output hashes.

Only A0–A6 green permits `CORE-D2-099` and parent-gate closure.

## Gate authority

| Decision | Authority |
|---|---|
| Program/WBS contract | Ethan |
| Board release and dependency enforcement | Grace |
| Resolver and activation architecture | Gena |
| Implementation and focused tests | Felix |
| Independent reproducibility/integrity verification | Chiron |
| Sampled relation interpretation | Colombo |
| Artifact-safety review | Daniel |
| Schedule and infra-duration disposition before W1 | Sophia |
| Final activation acceptance | Ethan after Gena and Chiron evidence |

No single implementation owner may author a gate, choose its release threshold after seeing release output, and approve the same gate.

## Failure and rollback rules

- Missing evidence yields PAUSED, never inferred green.
- Red CI pauses code rows.
- Invalid or unstable artifacts remain quarantined.
- A canary regression immediately returns the active pointer to `last_known_good`.
- Rollback success is proven by output hashes and runtime metadata, not merely by process health.
- Failure does not authorize the old mock artifact or a degraded-profile pass.

## W0 exit

W0 closes only when:

1. this contract is linked and signed;
2. CHI-015 status is reconciled;
3. the detailed state, segmentation, statistics, agreement, and identity contracts are complete;
4. Gena's architecture review is accepted;
5. schedule/infra-duration disposition is recorded;
6. Grace verifies links and releases W1.

---
SIGNED: Architecture (Ethan) | Hesperia core/default context | 2026-09-16 | CORE-D2-001 real Dict D program contract
