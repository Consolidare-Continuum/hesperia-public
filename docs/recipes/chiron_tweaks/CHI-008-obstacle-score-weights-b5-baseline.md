# CHI-008 — Obstacle-score weights (B5): live, held; "CI-enforced" sum check isn't actually wired into CI

## 1. Task/goal

Fourth Tier B pack (grind order: B8 done → B6 blocked → B2 done → **B5** next, "constrained,
low-risk by construction"). Review the 3 registry-named candidates (`w_decay`, `w_guard_obs`,
`w_shadow_obs`, `core/math/core_math.py` `DEFAULT_CONFIG`) and specifically check the registry's
own claim: "CI-enforced to sum to 1.0 — literally cannot move independently." Same discipline as
CHI-006/CHI-007: verify the enforcement claim against the actual call graph before accepting it.

## 2. Where the three candidates live and what consumes them

`core/math/core_math.py::DEFAULT_CONFIG` — `w_decay=0.50`, `w_guard_obs=0.30`, `w_shadow_obs=0.20`
(lines 58-60). Feed `metric_obstacle_score()` (line 383-397):

```
obs = w_decay * Loss + w_guard_obs * clamp(GuardCount, 0, 1) + w_shadow_obs * clamp(shadow_hops / max_shadow_hops, 0, 1)
```

`metric_obstacle_score` is called twice inside `core_math.py` itself (`_analyze_raw`/`analyze`,
lines 577, 660) — a genuinely central, load-bearing composite in the sealed core physics, not an
orphan. `runtime/pipeline/analyze.py` imports `core_math.analyze` directly and is in turn called
by `research/clinical_tfp/product_analyze.py`, `runtime/pipeline/run_e2e_sentence.py`,
`runtime/pipeline/run_e2e_all.py`, and `runtime/pipeline/run_tfp_file_pipeline.py` (via
`06_product_analyze.json`) — wide-reaching, unlike B6.

## 3. The registry's claim, checked against the actual call graph

Registry: "CI-enforced to sum to 1.0 — literally cannot move independently." Wiki
(`metric_obstacle_score` page): "building a config where these three don't sum to 1 fails CI...
CI-enforced sum = 1.0 ± 1e-6." Traced where that check actually lives and what invokes it:

- `core_math.py::validate_config()` (lines 144-175) does contain the exact check:
  `if abs((w_decay + w_guard_obs + w_shadow_obs) - 1.0) > 1e-6: errs.append(...)`. Correct, real
  code.
- **`validate_config()` has zero callers anywhere in the repository except `core_math.py`'s own
  `run_tests()` function** (its self-contained invariant/contract harness, not a pytest file).
  `run_tests()` is itself only invoked via `python core/math/core_math.py test` from the command
  line (`if __name__ == "__main__"` block) — grepped every `.github/workflows/*.yml` and every
  file under `tests/`, none call `run_tests()`, `validate_config()`, or `python core/math/core_math.py
  test`.
- So the sum-to-1.0 check is real, correct, and would catch a bad config — **if anyone ever ran
  it**. It is not part of pytest CI or any GitHub Actions workflow today. "CI-enforced" overstates
  it; "self-test-enforced, reachable only by manual invocation" is accurate.
- No current drift risk in practice: `assets/config/guard_config_v1.json` (the live config file)
  matches `DEFAULT_CONFIG` exactly (`0.50`/`0.30`/`0.20`, sum `1.0`) — confirmed by direct read,
  not assumed.

Smaller in kind than CHI-006 (the metric itself is genuinely live, wide-reaching, and correctly
computed — not dead code) but the same category of finding: a "CI-enforced" claim in the
catalog/wiki that doesn't survive a direct trace to an actual CI step.

## 4. Real evidence — the metric computing correctly, and a real-session scope note

- `python core/math/core_math.py test`: **7 passed, 0 failed**, including
  `validate_config: expected no errors for default config` — run directly this session, not
  assumed from reading the code.
- `python core/math/core_math.py` (demo mode): real computed `obstacle_score: 0.13930521086877806`
  on the module's own synthetic demo vectors — confirms the formula executes and produces a
  sane, in-range value.
- `tests/test_e2e_flows.py`, `test_invariant.py`, `test_attribution.py`, `test_adversarial.py`,
  `test_guard_pipeline.py`, `test_engine_analyze_contract.py`: all pass, exercising this same
  `analyze()`/`metric_obstacle_score` code path on the default (English) profile.
  `test_metric_analyze_emit.py` has 2 pre-existing failures — confirmed unrelated to B5 (fixture
  drift on `analyze_profile_meta`/`area_math_grain` fields the comparison fixture predates,
  `obstacle_score` appears only as a static `1.0` placeholder in that file's fixture dict, never
  exercises the real weight computation) and definitionally pre-existing since no code was changed
  this session.
- **Scope note, not a bug**: re-inspected CHI-005/CHI-007's real RU-language TFP session bundle
  (`outputs/tfp/runs/chi005_b8_baseline/06_product_analyze.json`) — `runtime.pipeline.analyze.analyze()`
  returned `"_error": "semantic_vacuum: no tokens matched any dictionary"` for that session. This
  matches the already-documented architecture split (deployment map, PC-001): the TFP/Russian lane
  resolves concepts via DLCR against the sealed Russian dict pack, while `core_math.analyze()`'s
  sealed multiscale path expects the English lexicon. So `metric_obstacle_score`/B5's weights are
  real and load-bearing for the **default (English) analyze profile**, but do not currently
  produce a value for real TFP/Russian clinical sessions run through the batch pipeline — not a
  new finding, a known, already-documented boundary, recorded here because it's directly relevant
  to what "real-session validation" can mean for this specific pack.

## 5. Verdict: hold at current defaults

No evidence to move `w_decay=0.50`, `w_guard_obs=0.30`, or `w_shadow_obs=0.20` — the split (half
weight on decay loss, less on guard/shadow penalties) is coherent and the sum constraint is
mathematically necessary for the composite to stay in `[0,1]`, not itself a tuning question.
`validate_config()`'s check is correct and worth wiring into pytest as a small, real follow-up
(see §9) — a documentation/CI-hygiene item, not a parameter-value question.

## 6. Config

No change. `DEFAULT_CONFIG` and `guard_config_v1.json` both remain `w_decay=0.50`,
`w_guard_obs=0.30`, `w_shadow_obs=0.20`.

## 7. Invocation (for reference)

`python core/math/core_math.py test` runs the module's own self-test harness (7 checks including
`validate_config`); `python core/math/core_math.py` (no args) runs the demo and prints a live
`obstacle_score`. Both run directly against `DEFAULT_CONFIG`/`load_config()`, no TFP-specific
setup needed — this is default-profile sealed core math, not the TFP lane.

## 8. Expected output shape (unchanged)

`obstacle_score` in `[0,1]`, one float per `analyze()` call, part of the standard
`_analyze_raw()`/`analyze()` composite output alongside `governance`, `loopability`,
`tension_energy`.

## 9. Rollback / doc corrections + real follow-up flagged

No code rollback needed — nothing changed. `CANDIDATE-REGISTRY.md`'s B5 row updated to soften
"CI-enforced" to the accurate "self-test-enforced, not wired into pytest CI" and mark
reviewed/held. **Real, small follow-up worth a future task** (not done here — out of scope for a
review pass, and wiring a new pytest assertion is closer to a documented-parameter-adjacent CI fix
than a calibration move): add a one-line `tests/test_core_math_config.py` that calls
`validate_config(load_config())` and asserts no errors, so a future edit to `guard_config_v1.json`
or `DEFAULT_CONFIG` that breaks the sum-to-1.0 invariant actually fails CI instead of only failing
a manual `python core/math/core_math.py test` nobody runs by default. Flagging to `inbox.md` for
Grace triage rather than adding the test unilaterally mid-review.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | B5 reviewed via full thinking-map/self-test/pytest toolchain, verdict: hold at current defaults; "CI-enforced" claim traced and corrected (self-test-only, not wired into pytest); real-session scope boundary (English profile only) documented, not a new bug
