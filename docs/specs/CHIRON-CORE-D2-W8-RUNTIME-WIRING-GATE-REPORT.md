# Gate report — CORE-D2 W8 runtime context and shadow calibration

**Tasks:** `CORE-D2-080..089`
**Date:** 2026-09-16
**Authority note:** Felix, all W8 roles, explicit operator authorization ("execute solo through activation," 2026-09-16). This is the highest-risk wave so far — it touches the live production resolver pipeline (`core/engine/lexical_concept/pipeline.py`, `core/resolver/resolver.py`) directly, not just calibration tooling.

## Result

**PASS** — with the critical invariant proven both at the unit level and against the real production golden-corpus regression suite.

## What was built

1. **`CORE-D2-080`** — `hesperia/engine/calibration_dict_paths.py`: `resolve_dict_d_file()` and `calibration_manifest()` extended with `dict_d`/`dict_d_hash`/`dict_d_enabled` (hardcoded `False` — a present file never self-activates).
2. **`CORE-D2-081`** — `_analyze_internal()` loads Dict D once per runtime context (`load_dict_d_pairs`, not per-hit/per-segment).
3. **`CORE-D2-082/083`** — `dict_d_pairs` threaded through both resolver call sites in `pipeline.py`.
4. **`CORE-D2-084`** (the architectural fix) — `core/resolver/context.py` gained `paragraph_spans`/`paragraph_index_for_span` (blank-line-delimited, duplicated minimally from the calibration-side rule per the existing `dict_d_index.py` layering precedent) and `coherence_from_empirical_traced`. `core/resolver/resolver.py` gained `resolve_paragraph_hits()` — the two-pass baseline-then-rescore process the W0 contract requires — and `resolve_hit()` gained a new, **separate** `empirical_context_ids` parameter so the empirical (D) context is never conflated with `coherence_from_related`'s same-hit sibling candidates (the exact violation Gena's W0 review flagged as still-live going into this wave).
   - Call site 1 (whole-text flat hit list): a lightweight baseline pre-pass groups hits by paragraph and computes each one's baseline winner *before* the existing sequential loop runs, so the pre-existing, unrelated `sequential_association_weight`/`recent_winners` mechanics stay byte-for-byte untouched.
   - Call site 2 (`segment_by_newlines` loop): each segment already *is* one paragraph grouping, so its per-hit loop was replaced outright with one `resolve_paragraph_hits()` batch call.
5. **`CORE-D2-085`** — `resolve_hit`'s audit trail gained `empirical_pair_concept_id` (which sibling produced the winning NPMI pair) and `empirical_context_size`; `_analyze_internal`'s `resolver_trace` gained `dict_d_pairs_loaded`.
6. **`CORE-D2-086`** — shadow comparison test proves a *present* Dict D file produces byte-identical `span_resolutions`/`unresolved_span_resolutions`/`family_activation`/`area_activation` to no Dict D file at all, while weight stays 0.
7. **`CORE-D2-087`** — test-only weight-sweep harness (`tests/lexical_concept/test_dict_d_shadow_comparison.py::weight_sweep`), never touches `engine_constants.json`.

## Commands and results

```text
$ python -m pytest -q tests/lexical_concept/test_paragraph_context_wire.py
.........
9 passed

$ python -m pytest -q tests/lexical_concept/test_dict_d_shadow_comparison.py
.....
5 passed

$ python tools/check_dlcr_regression.py
DLCR regression OK (all corpora)

$ python -m pytest -q tests/lexical_concept tests/dict_calibration
[all dots, no failures]

$ python -m pytest -q tests/experimental/clinical_tfp/test_crossplane_contradiction.py \
    tests/experimental/clinical_tfp/test_dlcr_benchmark_sessions.py \
    tests/lexical_concept/test_determinism_lock.py \
    tests/lexical_concept/test_noise_sensitivity.py \
    tests/test_tfp_calibration_wave002_smoke.py \
    tests/test_tfp_module_v1_dlcr_golds.py \
    tests/test_tfp_rel_realism_enf.py
[all dots, no failures — every test that directly exercises run_dlcr_pipeline/_analyze_internal]
```

## The critical invariant, proven three separate ways

CORE-D2-088 requires "verify real empirical hits, live no-op at zero, no interface
leakage." All three, independently:

1. **Live no-op at zero**: `test_resolve_paragraph_hits_weight_zero_identical_to_single_pass_baseline`
   (function level) and `test_dict_d_present_at_weight_zero_is_a_pure_shadow_no_behavior_change`
   (full-pipeline level, real production dict_a/dict_b, real `run_dlcr_pipeline`)
   both hold with a deliberately strong (`npmi=0.9`) Dict D pair present — not a
   trivially-empty-input test.
2. **Real empirical hits when nonzero**: `test_resolve_paragraph_hits_nonzero_weight_uses_cross_hit_context`
   and `test_weight_sweep_score_nondecreasing_for_positive_empirical_signal` both
   run at `empirical_weight_override=1.0` (test-only override, no production
   config touched) and observe the score actually move, with the correct
   sibling ID recorded in `empirical_pair_concept_id`.
3. **No interface leakage**: `test_resolve_hit_empirical_context_defaults_to_empty_not_same_hit_siblings`
   proves that calling `resolve_hit` *without* an explicit `empirical_context_ids`
   (i.e. every pre-existing caller, unmodified) never lets same-hit candidate
   siblings leak into the empirical channel — the W0-forbidden case.

`tools/check_dlcr_regression.py` (the repo's own pre-existing golden-corpus
regression gate, which calls `resolve_hit` directly across `seed_en` and
`tfp_ru` suites) passes unchanged — confirmed both by running it and by code
inspection: `coherence_from_empirical`/`coherence_from_empirical_traced`
short-circuit to `(0.0, None)` whenever `dict_d_pairs` is falsy, and this tool
never passes `dict_d_pairs`, so the new default empirical-context value is
unreachable code for it regardless.

## Note on suite scope

An attempt to run the entire repo-wide `pytest tests/` (every subsystem —
physics validation, TRIZ, KME, etc., not just the paths this wave touches)
was killed by an environment timeout before producing any output — not a
test failure, no signal either way from that run. Every test file that
directly imports/calls `run_dlcr_pipeline`, `_analyze_internal`, or
`resolve_hit` was identified by grep and run explicitly instead (listed
above, all green), which is the actually-relevant regression surface for a
resolver/pipeline change; not claiming broader coverage than that.

## What this does not cover yet

- No real Dict D data exists — every test above uses synthetic pairs.
- The W9 activation weight value is not decided here.
- `core/resolver/dict_d_index.py`'s `load_dict_d_pairs` still silently skips
  malformed rows at the runtime layer (by design — it's a lookup table, not a
  calibration-time validator; `tools/dict_calibration/dict_d_io.py` from W6
  is the fail-closed validator, used at build/gate time, not runtime-hot-path
  time). Not a regression; documented in the original module docstring since
  before this wave.

## Release

W9 (`CORE-D2-090..099`, atomic activation and rollback) is released.

---
SIGNED: Felix (all W8 roles, explicit operator authorization) | Claude Code context | 2026-09-16 | CORE-D2 W8 gate
