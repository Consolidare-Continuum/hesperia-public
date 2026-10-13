# Gate report — CORE-D2 W9 atomic activation and rollback

**Tasks:** `CORE-D2-090..099`
**Date:** 2026-09-16
**Authority note:** Felix, all W9 roles, explicit operator authorization ("execute solo through activation," 2026-09-16).

## Result

**MECHANISM PASS. PROGRAM NOT CLOSED.** The activation/rollback machinery is
built and tested end-to-end against a real (not hand-faked) v2 candidate
bundle. The actual production activation this wave exists to gate — a real
Dict D, a real selected weight, a real flip of
`resolver.coherence_empirical_weight` — has **not** happened and is not
claimed here.

## What was built

1. **`CORE-D2-090`** — `docs/specs/ETHAN-CORE-D2-W9-ACTIVATION-CRITERIA.md`:
   fixes the weight-selection *procedure* (sweep against W7's frozen limit
   policy, take the smallest weight past which resolutions meaningfully
   change) without selecting a number — there is no real data to select one
   against yet.
2. **`CORE-D2-091..096`** — `tools/dict_calibration/pack_activation.py`:
   `activate_pack` (atomic pointer swap, single-file `last_known_good`
   history, refuses non-`candidate`/`release_candidate` states),
   `validate_active_pack` (re-derives bundle identity from scratch every
   call, fails closed on any post-activation mutation),
   `rollback_to_last_known_good` (one level of history, fails closed on a
   second consecutive rollback), `post_activation_smoke` (fixed-input
   metadata check).
3. **`CORE-D2-097/098`** — proven directly in tests, not simulated: activate
   bundle A, activate bundle B (genuinely distinct, both produced by the
   real `release_freeze.freeze_core_candidate`), roll back, and confirm the
   restored pointer's `bundle_id`/`manifest_sha256` are byte-identical to
   bundle A's original activation record.

## Commands and results

```text
$ python -m pytest -q tests/dict_calibration/test_pack_activation.py
.......
7 passed

$ python -m pytest -q tests/dict_calibration tests/lexical_concept
[all dots, no failures — full suite, same commit]
```

## Notable finding during construction

`release_freeze.freeze_core_candidate` publishes bundles **read-only**
(deliberate immutability enforcement). Two of the seven tests needed
`chmod(0o644)` before mutating a file to actually simulate tampering — the
first attempt hit `PermissionError` from the filesystem itself before
`pack_activation.py`'s own logic ever ran. Kept as a genuine tamper
simulation (chmod-then-mutate) rather than weakened into a `monkeypatch` of
the validation function, since the real value of `CORE-D2-098`'s test is
proving detection works against bytes that actually changed on disk.

## Why this wave does not close CORE-D2 / unpause CORE-S2-LIVE-04

`CORE-D2-099`'s literal text is "Receive Ethan/Gena final acceptance; close
CORE-D2 and unpause parent closure." Accepting that today would mean
declaring the *parent gate* (CORE-S2-LIVE-04, which exists specifically to
keep `coherence_empirical_weight` at `0.0` until Dict D is real) satisfied
while:

- Dict D is still the 2026-09-04 mock build — never rebuilt from real data.
- `CORE-D2-049-C/D` (the clean-generation rerun) has not run — deliberately
  deferred, real cost, operator's call for when.
- `CORE-D2-090`'s own weight-selection procedure has nothing to select
  against yet.

Mechanically closing CORE-D2 without any of that would be the same category
of mistake this whole program was built to prevent — a green checkmark
standing in for real evidence. **CORE-D2-099 is left open.** `CORE-S2-LIVE-04`
stays PAUSED. W0-W9's tooling is complete and tested; what remains is the
real generation run plus threading its output through this now-ready
machinery — genuinely smaller work than what W1-W9 just did, but not zero,
and not mine to schedule unilaterally given the deferred-cost decision
already made this session.

---
SIGNED: Felix (all W9 roles, explicit operator authorization) | Claude Code context | 2026-09-16 | CORE-D2 W9 gate — mechanism only, program not closed
