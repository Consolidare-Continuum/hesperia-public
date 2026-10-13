# Gate report — CORE-D2 W5 deterministic Dict D builder

**Tasks:** `CORE-D2-050..059`
**Date:** 2026-09-16
**Authority note:** Implemented, verified, and released solo by Felix under explicit
operator authorization ("execute solo through activation," 2026-09-16) — this
report combines the implementer, Chiron-verification, and Grace-release roles
rather than three independent sign-offs. Flagged here rather than presented as
independent review.

## Result

**PASS** (implementation-level, against synthetic fixtures — no real corpus
data exists yet; `CORE-D2-049-C/D` full-corpus release evidence is still
outstanding and this wave does not depend on it having landed).

## What was built

`tools/dict_calibration/dict_d_builder.py` — consumes a schema-valid
`hesperia.dict_d.resolved_corpus.v1` export (validated via the existing
`resolved_export.validate_resolved_export`, not reimplemented) plus a
candidate Dict B's canonical relations, and computes Dict D rows per the W0
locked statistical contract (`ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md`):

- one pair-event per unordered distinct-concept pair per paragraph, concepts
  deduplicated within a paragraph before pairing (CORE-D2-052);
- explicit `N`/marginals over every paragraph including zero-concept ones
  (CORE-D2-053);
- bounded NPMI with the perfect-co-occurrence (`n_ij=n_i=n_j=N`) exact-`1.0`
  special case (CORE-D2-054);
- non-negative Dunning G² from the complete 2×2 contingency table, zero cells
  contribute 0 (CORE-D2-055);
- the evidence floor (default 5, matching the existing schema's `cooc_count`
  minimum) applied strictly as a post-hoc release filter — verified by test
  that it changes only `rows`/`n_pairs_released`, never the underlying counts
  feeding other pairs (CORE-D2-056);
- stable canonical row order (`concept_id_a`, `concept_id_b` lexicographic),
  `source_books`, and a separate build-metadata sidecar with a `rows_sha256`
  binding (CORE-D2-057);
- runtime rows carry only `agrees`/`novel` — `contradicts` is never emitted
  (matches the W0 contract's review-only semantics).

Fail-closed: rejects malformed resolved exports (delegates to the existing
validator), negative evidence floors, zero-paragraph exports (`N<=0`), and any
non-finite/out-of-bounds NPMI or negative contingency cell.

## Commands and results

```text
$ python -m pytest -q tests/dict_calibration/test_dict_d_builder.py
.............
13 passed

$ python -m pytest -q tests/dict_calibration/test_dict_d_builder.py   # pass 2, same commit, same input
.............
13 passed
```

Full regression sweep, same commit:

```text
$ python -m pytest -q tests/dict_calibration tests/lexical_concept
[all dots, no failures]
```

### Independent NPMI/G² cross-check (CORE-D2-058 determinism/correctness discipline)

`test_npmi_and_g2_match_independent_reference_computation` recomputes both
statistics from the same 2×2 contingency table using a second, independently
written formula in the test itself (not by calling the builder's internal
helpers) and asserts agreement to `1e-12` relative tolerance on a
hand-verified 5-paragraph, 3-book fixture (`N=5, n_A=3, n_B=3, n_AB=2`).

### Byte-identity determinism (CORE-D2-058)

`test_two_builds_from_identical_input_are_byte_identical` runs
`build_dict_d` twice on identical input and asserts the canonical JSONL rows
and summary bytes (including the `rows_sha256` binding) are byte-for-byte
equal.

## What this does not cover yet

- No real Dict D has been built — only synthetic fixtures. The builder is
  ready to consume a real `CORE-D2-049-D`-verified resolved-corpus export
  once one exists; that full-corpus generation is a separate, explicitly
  deferred cost (see `operational/assignments/hesperia-core-s2/` session
  notes, 2026-09-16).
- `assets/schemas/lexical_concept/dict_d.schema.json` and `dict_d_io.py`
  still reflect the pre-W0 permissive shape — tightening them is W6
  (`CORE-D2-060..069`), not this wave.
- Agreement-label review (`contradicts` review-only auditing) is W7's
  sampling/stability wave, not built here.

## Release

W6 (`CORE-D2-060..069`, schema/integrity tightening) is released.

---
SIGNED: Felix (all W5 roles, explicit operator authorization) | Claude Code context | 2026-09-16 | CORE-D2 W5 gate
