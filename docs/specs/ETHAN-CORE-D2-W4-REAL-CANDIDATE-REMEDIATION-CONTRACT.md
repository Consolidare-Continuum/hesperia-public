# Ethan contract — CORE-D2 W4 real-candidate remediation

**Task:** `CORE-D2-049-A`  
**Date:** 2026-09-16  
**Status:** RATIFIED — remediation contract only  
**Parent contract:** `ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md`  
**W1 evidence:** `CHIRON-CORE-D2-W1-FREEZE-GATE-REPORT.md`  
**W3 contract:** `ETHAN-CORE-D2-W3-CORE-PACK-GATE-CONTRACT.md`  
**W4 evidence:** `CHIRON-CORE-D2-W4-RESOLVED-EXPORT-GATE-REPORT.md`

## Decision

The W4 implementation gate is green, but the real full-corpus gate remains
**PAUSED**. A new, clean, generation-bound LIVE-06 candidate must be produced,
materialized, frozen, compared, gated, and exported. The existing
`outputs/dict_calibration/live_v1_2026-09-14/` directory is inspection evidence
only and is forbidden as release evidence.

This contract authorizes only the bounded remediation tasks `CORE-D2-049-B..D`.
It does not promote a bundle, select an active pack, change
`resolver.coherence_empirical_weight = 0.0`, or release W5.

## Observed LIVE-06 gap

The independently inspected work directory contains:

- `dict_b_draft.jsonl`: 63,856 rows;
- `dict_b_anchored.jsonl`: 53,272 rows;
- `dict_a_to_b_links.jsonl`: 63,104 rows;
- `dict_a_engine.jsonl`: 63,104 rows;
- `dict_b_rejected.jsonl`: 10,584 rows.

It does not contain a candidate `manifest.json`, a
`manifest.json.sha256`, any frozen Dict C source/intermediate/runtime artifact,
or a full-corpus resolved export. Its available `evaluation_run.json` is the
old five-text `dict_calibration_eval_v1` output, not
`hesperia.dict_calibration.bundle_comparison.v1`.

The producer artifacts also require deterministic materialization:

- producer Dict A carries fields outside the strict W3 runtime schema;
- anchored Dict B repeats concept IDs and therefore is not directly canonical;
- proposal and rejection records are separate producer streams;
- no authored Dict B edge row is evidenced by the inspected anchored rows;
- `dict_a_to_b_links.jsonl` exists, but no source → intermediate → runtime Dict C
  lineage has been frozen.

The tracked `v0_core_syzif_001` offline/mock seal is not a substitute. Missing
evidence is not inferred green.

## One clean generation

`CORE-D2-049-C` must start in a new, empty generation directory. It must rerun
the producer from the pinned source corpus and pinned code revision; it may not
copy, rename, patch, filter, or use as a cache any generated file from
`live_v1_2026-09-14`.

Before generation starts, one canonical generation ledger must be written and
its SHA-256 independently recorded. The ledger is immutable after the first
producer byte is emitted and contains exactly:

- `schema = hesperia.dict_calibration.generation_ledger.v1`;
- a unique `generation_id`;
- the absolute non-symlink corpus root used for execution;
- the complete stable relative-path → SHA-256 source map;
- the source-map count and canonical source-map SHA-256;
- the exact Hesperia Git commit and a clean-tree assertion;
- SHA-256 values for every producer, materializer, evaluator, gate, exporter,
  resolver, and configuration file used;
- exact model provider and model identifier;
- exact checkpoint identifier, or the literal `none` when the provider exposes
  no checkpoint;
- exact prompt path and prompt-bytes SHA-256;
- all generation-affecting configuration and environment values;
- random seed, worker count, batch size, batch ordering rule, and retry policy;
- generation start timestamp as metadata only, excluded from ordering and
  artifact-content decisions.

`generation_id` is the lowercase SHA-256 of canonical JSON containing every
ledger field above except `generation_id` and the informational timestamp.
Canonical JSON means UTF-8, sorted object keys, no insignificant whitespace,
finite JSON numbers only, and one terminal LF.

Any dirty code tree, source-map mismatch, prompt/model/checkpoint ambiguity,
missing file digest, undeclared generation-affecting setting, or change after
the ledger pin fails closed. A retry after any such failure uses a new empty
generation directory and a new ledger; it does not resume the failed release
generation.

## Deterministic materialization rules

Materialization consumes only producer files from the one ledger-bound
generation. Every input is a regular non-symlink file under that generation
root. Duplicate JSON keys, blank JSONL records, malformed UTF-8/JSON, unknown
fields where an exact producer shape is required, non-finite numbers, unsafe
paths, and input mutation during the operation fail closed.

All emitted JSONL uses one canonical compact JSON object per line, UTF-8,
sorted keys, finite numbers only, and a terminal LF when at least one row
exists. Rows use the sort keys frozen below. Sorting never depends on producer
filesystem order, process count, locale, hash seed, or model return order.

### Dict A — strict projection

Each producer `dict_a_engine.jsonl` row must have exactly:

`entry_id, surface_form, normalized_form, match_type,
candidate_concept_ids, priority, version`.

The release Dict A row is the strict projection:

`entry_id, normalized_form, match_type, candidate_concept_ids`.

No value is recomputed. `surface_form`, `priority`, and `version` are discarded
and no other producer field may pass through. `entry_id` and
`normalized_form` must be non-empty; `match_type` must be one of the W3
supported values; candidate IDs must be non-empty, unique, already in canonical
lexicographic order, and closed over materialized Dict B.

Rows are sorted by `(normalized_form, match_type, entry_id)`. Duplicate
`entry_id` or duplicate `(normalized_form, match_type)` fails closed even when
the rows are otherwise identical. Materialization must not merge Dict A rows.

### Dict B — canonical projection and bounded collapse

Each anchored producer row is projected to exactly:

`concept_id, related_concept_ids, area_ids, family_ids`.

`concept_id` and `related_concept_ids` are required. Missing `area_ids` or
`family_ids` is represented by omission, not an invented empty list. Present
lists must contain unique non-empty strings in canonical lexicographic order.
All other anchoring, label, definition, score, reason, draft, version, status,
hex, and display fields are evidence-only and do not enter runtime Dict B.

Rows are grouped by `concept_id`. A repeated `concept_id` collapses to one row
only when every projected canonical object is byte-identical after canonical
serialization. If any canonical field is absent in one row and present in
another, or any canonical value differs, the group fails closed. The surviving
rows are sorted by `concept_id`.

Every `related_concept_ids` target must exist in the same materialized Dict B.
Self-relations, duplicate targets, asymmetric authored relations, or a claimed
relation without separately mapped authored-edge evidence fail closed.

### Proposal and rejection evidence

`dict_b_draft.jsonl`, `dict_b_anchored.jsonl`, and
`dict_b_rejected.jsonl` form one proposal disposition ledger. Each draft
receives a deterministic `proposal_id` equal to the SHA-256 of its canonical
producer row plus NUL plus its zero-based producer ordinal.

Exactly one disposition must exist for every `proposal_id`:

- `outcome = anchored` records `proposed_concept_id`, the canonical
  `anchor` concept ID, producer bind score/reason, and source producer ordinal;
- `outcome = rejected` records `proposed_concept_id`, producer `reason`,
  finite `best_score`, `detail`, and source producer ordinal; it has no
  `anchor` field.

An anchored row maps through its `calibration_draft_id` plus exact
`calibration_from_lexical` / draft `from_lexical` content; a rejected row maps
through its embedded canonical `draft` object. When multiple producer drafts
are byte-identical under that evidence key, dispositions consume the lowest
unmatched producer ordinal. Exact multiset counts must close: any residual,
differing-content ambiguity, unknown proposal, multiple dispositions for one
ordinal, missing disposition, invented anchor, or changed producer value fails
closed.

The frozen `dict_b_proposal_evidence` schema must accept these two exact tagged
variants. It must not coerce a rejection into an anchored row merely to satisfy
the old non-empty `anchor` assumption. Evidence rows are sorted by
`proposal_id`.

### Truthful zero authored-edge evidence

The inspected producer Dict B has no evidenced authored relation in
`related_concept_ids`. Therefore the clean generation may report zero authored
edges only if the clean rerun independently reaches the same truthful result.
No placeholder, self-edge, sentinel, copied mock edge, or synthetic row may be
emitted.

The release authored-edge file is then exactly zero bytes and has SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The release freeze manifest and W3 core-pack gate must use
`hesperia.dict_calibration.freeze_manifest.v2`. Every artifact descriptor adds
an exact non-negative `row_count`. For
`dict_b_authored_edge_provenance` only, the descriptor may carry:

```json
{"evidence_status":"truthful_zero","path":"evidence/dict_b_authored_edges.jsonl","row_count":0,"sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","status":"authored_edge_provenance"}
```

For that role, `row_count = 0` is valid only with
`evidence_status = truthful_zero`, exact empty-file bytes, exact empty digest,
and zero `related_concept_ids` across canonical Dict B. If any canonical B
relation exists, truthful-zero status fails closed and complete edge rows are
required. Every other required runtime or evidence artifact remains non-empty.
For non-zero authored-edge evidence, `evidence_status = present`,
`row_count > 0`, and every row must map exactly one canonical unordered edge.

The freeze and gate must recompute all row counts. A count/status/file/content
disagreement fails closed. Manifest v1 remains historical W1 evidence but is
not eligible for this real release generation.

### Dict C — derivation and lineage

Dict C is derived only from the clean generation's
`dict_a_to_b_links.jsonl`; it is not copied from Dict A and is not generated
from raw corpus substring matching.

For every source link, emit one source-evidence row with:

`link_id, lexical, concept_id, match_type, priority, source_ordinal`.

`link_id` is the SHA-256 of the canonical producer link plus NUL plus its
zero-based producer ordinal. Values are preserved exactly and `concept_id`
must exist in canonical Dict B.

The intermediate artifact groups source rows by exact `lexical`. It emits:

`normalized_form, candidate_concept_ids, priority, source_link_ids`.

Candidate IDs are the sorted unique IDs from that lexical group. `priority` is
the maximum exact producer priority in the group; ties do not alter ordering.
`source_link_ids` is sorted and complete. No normalization beyond the producer
`lexical` bytes is permitted.

The runtime Dict C projection is exactly:

`normalized_form, candidate_concept_ids, priority`.

Runtime rows are sorted by `normalized_form`; duplicates fail closed. The
manifest records all three artifact hashes and row counts. Each intermediate
row must close over source `link_id` values, and each runtime row must equal the
strict projection of exactly one intermediate row. Missing, extra, ambiguous,
or mutated lineage fails closed.

## Release freeze CLI

`CORE-D2-049-B` must provide one release-only entry point:

```text
python tools/freeze_core_candidate.py \
  --producer-dir DIR \
  --generation-ledger FILE \
  --generation-ledger-sha256 DIGEST \
  --evaluation-metrics FILE \
  --destination DIR
```

All five inputs are required. The expected ledger digest is supplied from an
independent pin, not read from a sidecar created during the same invocation.
The destination must be absent or an empty directory. Publication is one
fsync-backed atomic rename from a sibling staging directory after complete
materialization, validation, sidecar generation, manifest-v2 identity
calculation, and final source revalidation.

The CLI exits `0` only after the destination is immutable and a second
read-back validation passes. It emits the generation ID, bundle ID, manifest
SHA-256, and deterministic artifact row-count/hash map. Any failure exits
non-zero, publishes no destination, removes its staging directory, and leaves
an initially empty destination empty. It never overwrites, promotes, activates,
changes an active pointer, edits runtime configuration, or accepts the legacy
freeze path without complete provenance.

## Candidate comparison and independently pinned limits

The real frozen candidate must be compared with the declared baseline using
`hesperia.dict_calibration.bundle_comparison.v1` on one stable, ordered sample
manifest. Baseline and candidate consume byte-identical sample text in the same
order. The report binds the real candidate bundle ID and must pass the W2
determinism and weight-zero requirements.

Before the clean generation begins, Ethan's limit policy must be serialized as
`hesperia.dict_calibration.limit_policy.v1` and independently pinned by
SHA-256. It contains the sample-manifest hash and the inclusive maxima for
accepted, rejected, coverage, entropy, and each family-distribution delta. It
contains no observed candidate metric or report hash.

After comparison, the W3 `hesperia.dict_calibration.limits.v1` envelope is
created mechanically: it copies the maxima byte-for-byte from the pinned
policy and adds only the candidate bundle ID and evaluation report SHA-256.
The gate receives both the pre-generation policy digest and the independently
recorded final limits-file digest. Any changed maximum, sample identity, late
policy creation, missing pin, forged delta, stale report binding, or digest
mismatch fails closed. Observing the candidate never authorizes threshold
revision.

The candidate comparison, frozen limits envelope, and a green deterministic
W3 verdict are prerequisites to full-corpus export. A green comparison does not
activate the candidate.

## Full-corpus export acceptance

`CORE-D2-049-D` may pass only when all of the following are green against the
same clean generation:

1. the generation ledger, real manifest-v2 candidate, candidate comparison,
   limit policy, limits envelope, and W3 verdict have matching identities and
   verified SHA-256 evidence;
2. the export CLI receives the real frozen candidate explicitly and forces
   Dict D disabled with effective weight `0.0`;
3. export source membership equals the ledger's complete source map exactly:
   no missing, extra, sampled, capped, skipped, symlinked, unreadable, or
   unsupported source;
4. exported book count equals the ledger source count and every book path/hash
   matches one ledger entry;
5. paragraph count equals an independent application of the frozen W0
   segmentation rule over every source, including paragraphs with zero
   resolved concepts;
6. resolved and unresolved partitions, offsets, winners, candidate scores,
   reason codes, resolver identity, configuration identity, bundle identity,
   source hashes, and corpus snapshot satisfy the W4 strict schema;
7. two clean exports into distinct empty destinations, with different
   `PYTHONHASHSEED` values and permitted worker scheduling, are byte-identical;
8. the canonical export SHA-256 and sidecar are retained as immutable gate
   evidence and independently recomputed by Chiron;
9. source, candidate, code, prompt, model/checkpoint, configuration,
   comparison, limits, or export mutation at any point is rejected before
   publication;
10. focused suites and the complete `tests/dict_calibration` and
    `tests/lexical_concept` suites are green at the pinned clean commit.

An exporter `--max-files`, sample mode, degraded mode, resumed partial output,
old LIVE-06 bytes, mock pack, stale candidate, unpinned threshold, or
prose-only count is not full-corpus evidence.

## Fail-closed disposition

The following produce **PAUSED**, never a warning or inferred pass:

- any attempt to reuse current LIVE-06 as release evidence;
- a missing or mutable generation ledger;
- producer/materializer schema drift;
- Dict A passthrough fields or duplicate identity;
- conflicting duplicate Dict B canonical projections;
- incomplete proposal disposition;
- invented authored-edge evidence or false truthful-zero status;
- broken Dict C source → intermediate → runtime lineage;
- manifest-v1 publication for the remediation candidate;
- absent/empty required artifacts other than explicitly truthful-zero authored
  edges;
- candidate comparison without pre-generation limits-policy pinning;
- limits changed after candidate observation;
- partial-corpus, non-repeatable, hash-mismatched, or mutation-exposed export;
- any mock, quarantined, degraded, contaminated, field-specific, or
  path-drifted input;
- any activation, pointer change, or non-zero empirical runtime weight.

## Handoff and release authority

- `CORE-D2-049-B` — Felix implements strict materialization, manifest-v2 zero
  evidence semantics, gate support, focused tests, and the release freeze CLI.
- `CORE-D2-049-C` — Felix performs one clean ledger-pinned rerun, freezes the
  real candidate, executes the candidate comparison, and produces the bound
  limits/gate evidence.
- `CORE-D2-049-D` — Chiron independently verifies identities, fail-closed
  behavior, full-corpus membership, two-build byte identity, and the immutable
  resolved-export checksum.
- `CORE-D2-049` — Grace may release W5 only after `049-B`, `049-C`, and `049-D`
  are DONE and their exact artifacts are linked.

No remediation task may activate A/B/C/D. Activation remains prohibited before
W9 and requires the separate parent-contract authority.

---
SIGNED: Team Lead (Ethan) | Hesperia CORE-D2 W4 remediation contract context | 2026-09-16 | CORE-D2-049-A
