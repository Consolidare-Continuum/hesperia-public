# PC-001 — TFP DLCR structural dict pin (full-stack, not fallback)

## 1. Task/goal

On the TFP analyze profile (`HESPERIA_ANALYZE_PROFILE=tfp`), make structural DLCR concept
resolution actually use the sealed, calibrated Russian dictionary pack instead of silently
falling back to a much smaller stack — without hard-pinning the version (an explicit override
must still win).

## 2. Parameters touched

| Parameter | Source | Code field | Default (pre-fix) | Recipe value |
|---|---|---|---|---|
| `HESPERIA_DLCR_STRUCTURAL` | env, gated via `hesperia/system/capabilities.py` | `apply_analyze_profile_defaults()` | unset (DLCR structural path off) | `"1"` (if-not-set default) |
| `HESPERIA_CALIB_DICT_VERSION` | env, consumed by `hesperia/engine/calibration_dict_paths.py` | `apply_analyze_profile_defaults()` | unset → silently fell through to `assets/data/engine_dynamics_v060/dict_{a,b}/*` | `"v0_6_0_clr_v052_5"` (if-not-set default) |

Neither parameter lives in `assets/calibration/dynamics_parameter_registry.yaml` /
`profiles_v1.json` / `semantic_field_equations_v1.json` / `core_math.py`'s `DEFAULT_CONFIG` —
they're runtime shipping-profile env gates (`runtime/shipping/analyze_profile.py`,
`runtime/shipping/env_guard.py`), not calibration-math parameters. Noted here per this doc's own
instruction to say explicitly when a combo isn't in those registries.

## 3. Combined rationale

These two must move **together**, not independently:

- `HESPERIA_DLCR_STRUCTURAL=1` alone turns structural DLCR *on*, but with
  `HESPERIA_CALIB_DICT_VERSION` unset it silently resolves against the small fallback stack
  (`assets/data/engine_dynamics_v060/dict_a,dict_b`, ~9–11 active concepts) — DLCR runs, but
  against the wrong dictionary, with no error or warning.
- `HESPERIA_CALIB_DICT_VERSION` alone (pinned but `HESPERIA_DLCR_STRUCTURAL` unset) never gets
  consumed — the structural DLCR call path that would read it never executes.
- Only both together route TFP analyze onto the sealed pack
  (`assets/calibration/dicts/v0_6_0_clr_v052_5/`: Dict B 283 concepts, Dict A 10155 token
  entries → 135 B ids, Dict C 24000 phrases → 212 B ids via `links.jsonl`).

This was a real bug, not a theoretical gap: `HESPERIA_CALIB_DICT_VERSION` had been deliberately
left unset by a prior "don't auto-pin the tiny `v0_tfp_cal_wave_002` wave" decision — correct in
spirit, but its side effect was that the *sealed* pack never got pinned either, defaulting
silently to the fallback instead. Not yet documented in `docs/foundations/parameter_synergies.md`
as of this recipe.

## 4. Config

Already shipped as the `if not (os.environ.get(...) or "").strip():` guard in
`runtime/shipping/analyze_profile.py::apply_analyze_profile_defaults()` (profile `"tfp"` branch,
lines ~56–66, Hesperia repo commit `3668bb0e`). No YAML/JSON edit needed to adopt this recipe —
it's the current default behavior of the `tfp` profile. To reproduce manually outside the
profile helper:

```bash
export HESPERIA_DLCR_STRUCTURAL=1
export HESPERIA_CALIB_DICT_VERSION=v0_6_0_clr_v052_5
```

## 5. Invocation

- Live: set `HESPERIA_ANALYZE_PROFILE=tfp` on the process/unit (e.g. `hesperia-analyze-tfp`
  systemd unit, port `:18881`) — `apply_analyze_profile_defaults()` applies both vars
  automatically if not already set.
- CLI/manual: `tools/gena_tfp_bundle_run.py -i <input> --gate-profile internal_review` with the
  two env vars exported as above, or via `hesperia_router_inquire(face="tfp", ...)` through the
  MCP tool.

## 6. Expected output shape

`engine_trace`/DLCR output should show real concept resolution — `concept_id`/`area_id`/
`family_id`/`activation` entries such as `TFP_SPLITTING`/A3/F5 or `TFP_COUNTERTRANSFERENCE`/
A10/F6 for clinical RU input — not a constant/near-empty result. `analyze_profile_meta()`'s
`dlcr_structural: true` and `calib_dict_version: "v0_6_0_clr_v052_5"` confirm the pin took
effect for that process.

## 7. Validation evidence

- `tests/test_dict_calibration_golden.py` + `tests/test_calibration_release_gate.py`: **4 passed**
  (re-run 2026-08-18 as part of this recipe, `python3 -m pytest` from repo root).
- Empirical before/after (Chiron, 2026-08-17, two RU clinical test statements, direct
  `run_dlcr_pipeline()` calls): `concept_weights` count **2→6** and **4→7**;
  `lexical_hits_accepted` **2→10** and **3→12**, once the pin is applied vs. left unset.
- **Full-pipeline sweep (2026-08-18, `tools/tfp_param_sweep.py`, first real use of the tool)**:
  `python3 tools/tfp_param_sweep.py --spec tests/fixtures/tfp/sweeps/dlcr_dict_pin_sweep.json`
  reproduces this combo across 3 named states on the tracked clinical-transcript fixture
  (`tests/fixtures/tfp/input.txt`) through the real `gena_tfp_bundle_run.py` pipeline, not a
  direct function call — `concept_weights` **8 → 8 → 30**, `lexical_hits_accepted` **10 → 10 →
  120**, dominant `(area/family)` shifts from `0/4` to `9/12` only once *both* env vars are set
  together (the middle "DLCR on, dict unset" state matches baseline exactly — confirms §3's
  claim that the flag alone changes nothing observable without the pin). Gate `pass: true` in all
  three. Report: `outputs/tfp/sweeps/dlcr_dict_pin/SWEEP-REPORT.md` (gitignored, regenerate on
  demand — the spec file is the durable, committed artifact).
- Full narrative: `project_tfp_dlcr_engine_trace_fix_2026-08-17` (brain-repo memory), section
  "corrected lexicon model + a second, bigger yield fix."

## 8. Rollback

Unset both, or set explicitly to the pre-fix values to force the fallback path back on:

```bash
unset HESPERIA_CALIB_DICT_VERSION   # or export HESPERIA_CALIB_DICT_VERSION=v0_tfp_cal_wave_002
unset HESPERIA_DLCR_STRUCTURAL      # or export HESPERIA_DLCR_STRUCTURAL=0
```

Since both are `if not already set` defaults (not hard pins), an explicit override at any layer
above `apply_analyze_profile_defaults()` already wins — no code change needed to roll back a
single deployment, only an env var change.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-18 | Hesperia TFP calibration zone
