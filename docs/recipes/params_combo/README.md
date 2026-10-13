# Recipes — parameter combos

One addressable place for recipes that document a **validated combination of ≥2 parameters**
used together — as opposed to a single-parameter toggle, which the generic shape in
[../README.md](../README.md) already covers on its own. Authored by Chiron
(`governance/SPEC-ETHAN-CHIRON-HESPERIA-CALIBRATION-ENTITY.md` §5a) whenever a calibration task
tunes more than one parameter at once for a stated goal.

## Addressing

- File: `PC-<NNN>-<slug>.md` — zero-padded 3-digit sequential ID, kebab-case slug.
  Example: `PC-001-ru-high-recall-diffusion.md`.
- ID assignment: next ID = highest ID currently in [INDEX.md](INDEX.md) + 1. Sequential, never
  reused, even if a recipe is later superseded — supersession is a status change in the index,
  not a freed number.
- Every new file gets an index row the same session it's authored. A `PC-*.md` file with no
  `INDEX.md` row is not addressable and does not count as shipped.

## Shape

Every combo recipe answers, in order:

1. **Task/goal** — what the caller actually wants, in one line.
2. **Parameters touched** — a table: parameter name → source registry file
   (`assets/calibration/dynamics_parameter_registry.yaml`, `profiles_v1.json`,
   `semantic_field_equations_v1.json`, or `core/math/core_math.py`'s `DEFAULT_CONFIG`) →
   `code_field` → default → recipe value.
3. **Combined rationale** — why these parameters move *together*, not the case for each in
   isolation. Cross-reference `docs/foundations/parameter_synergies.md` when the combo is a
   documented synergy/tension; say explicitly if it isn't yet documented there.
4. **Config** — the literal YAML/JSON diff or block to apply.
5. **Invocation** — how to actually run it (CLI/API/pipeline entrypoint).
6. **Expected output shape** — what a caller should see back, and how to tell it worked.
7. **Validation evidence** — what actually confirmed this combo works. Prefer
   `tools/calibration_release_gate.py --bundle-dir <bundle> --profile <profile>` output (the
   `11_calibration_release_gate.json` verdict) or the relevant `tests/test_*_calibration*.py`
   pass, over an ad hoc run's output — this repo already has a real, working calibration-release
   apparatus; use it before reaching for a router-inquire snapshot or inventing a new check. A
   combo recipe with no evidence field is a proposal, not a recipe — file it as feature theorizing
   (`../README.md` "When there's no recipe") instead until it has one.
   For a combo with more than one named state worth comparing side by side (baseline / partial /
   full, or several candidate values), use `tools/tfp_param_sweep.py --spec <sweep.json>` — it
   drives `gena_tfp_bundle_run.py` once per named combo and produces a single comparison table
   (`concept_weights`/`lexical_hits`/dominant area-family/gate pass) instead of several separate
   ad hoc runs. It orchestrates the same existing pieces, not a new evaluation method — commit the
   sweep spec JSON (`tests/fixtures/tfp/sweeps/*.json`) as the reproducible artifact; the run
   output under `outputs/tfp/sweeps/` is gitignored and regenerated on demand. First real use:
   `PC-001`.
8. **Rollback** — the exact values that restore defaults.

## When it isn't a combo recipe

A single parameter, alone → the generic shape in [../README.md](../README.md), no need for this
subdirectory. No documented combination of existing parameters reaches the goal → not a recipe
gap, a feature-theorizing note (`../README.md` §"When there's no recipe"), routed through
`inbox.md` → Grace triage like everything else.
