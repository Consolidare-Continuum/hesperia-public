# Ethan contract — CORE-D2 W9 activation criteria

**Task:** `CORE-D2-090`
**Date:** 2026-09-16
**Status:** RATIFIED — procedure only, no numeric weight selected
**Parent contract:** `ETHAN-CORE-D2-REAL-DICT-D-PROGRAM-CONTRACT.md`
**Authority note:** Felix, playing the Ethan role, explicit operator authorization ("execute solo through activation," 2026-09-16).

## What this contract does and does not do

Selecting "the smallest justified non-zero weight" for
`resolver.coherence_empirical_weight` requires evidence from a real Dict D
built on a real corpus — the W7 stability metrics, the W8 shadow comparison,
and a real weight-sweep against real graph data. **None of that evidence
exists yet.** Per the operator's explicit 2026-09-16 decision ("build
everything else first, rerun later"), the clean-generation rerun
(`CORE-D2-049-C/D`) that would produce it is deliberately deferred.

This contract therefore fixes the **procedure**, not the number. Selecting
an actual weight value against synthetic W7/W8 fixtures would be exactly the
kind of self-authored, unverifiable evidence this whole program exists to
prevent (see `CHIRON-CORE-S2-LIVE-04-GATE-ASSESSMENT-2026-09-16.md`, the
finding that started this program). No weight is chosen here.

## Activation selection procedure (to run once real data exists)

1. Take the W7 frozen limit policy (`ETHAN-CORE-D2-W7-SAMPLING-STABILITY-CONTRACT.md`)
   as the ceiling: any weight whose shadow-mode effect (via
   `resolve_paragraph_hits` with `empirical_weight_override` swept, per
   `CORE-D2-087`'s harness) pushes `family_activation`/`concept_activation`
   deltas past those frozen maxima is disqualified outright.
2. Within the surviving range, sweep weight from `0.0` upward in steps of
   `0.05` against the real frozen evaluation sample (the same
   `bundle_comparison.v1` sample used for the W3/core-pack gate — one
   consistent evidence trail, not a fresh sample chosen after seeing
   results).
3. Select the **smallest** weight at which a real, non-trivial fraction of
   candidate resolutions actually change relative to the `0.0` baseline
   (i.e. the point past which the empirical signal is doing real work, not
   just noise below the resolution of `saturate`'s clamp) — "smallest
   justified" means smallest sufficient, not smallest measurable.
4. That weight, the sweep data, and the disqualified-range reasoning all get
   written into a dated `ETHAN-CORE-D2-W9-ACTIVATION-WEIGHT-<date>.md`
   companion to this contract before `CORE-D2-091` proceeds — this document
   is deliberately not that file.

## Mechanism readiness (built and tested this wave, independent of the number above)

`tools/dict_calibration/pack_activation.py` — atomic activation, startup
re-validation, and one-level rollback, all tested end-to-end against a real
`freeze_core_candidate`-produced v2 bundle (not a hand-faked manifest):

- Activation is refused for any bundle not in `candidate`/`release_candidate`
  state.
- Startup validation re-derives the bundle's identity from scratch every
  time and fails closed on any artifact mutation since activation (tested by
  actually tampering a published artifact after activation).
- Rollback restores the prior `bundle_id`/manifest hash exactly, one level
  of history only — a second consecutive rollback with nothing behind it
  fails closed rather than guessing further back.

## What still blocks a real activation

1. `CORE-D2-049-C/D` (the clean-generation rerun) — not started.
2. This contract's own weight-selection sweep, step 4 above — cannot run
   without (1).
3. `CORE-D2-091..096`'s pack-pin mechanism is built and tested but has never
   been pointed at the real production `assets/config/engine_constants.json`
   / a real active-pack directory — only at synthetic `tmp_path` fixtures in
   this wave's tests.

`resolver.coherence_empirical_weight` stays `0.0` in
`assets/config/engine_constants.json`. This task does not change it.

---
SIGNED: Felix (Ethan role, explicit operator authorization) | Claude Code context | 2026-09-16 | CORE-D2-090
