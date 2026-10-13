# Recipes — Chiron tweaks

One addressable place for recipes that document a **genuinely usable new capability** Chiron
added to Hesperia's TFP calibration surface — as opposed to [params_combo/](../params_combo/README.md),
which is for tuning *existing* parameters together. A tweak belongs here when it's real, shipped,
tested code (not a proposal) that didn't exist as a parameter to combine in the first place.

## Addressing

- File: `CHI-<NNN>-<slug>.md` — zero-padded 3-digit sequential ID, kebab-case slug. Example:
  `CHI-001-tfp-corpus-truth-point-grounding.md`.
- ID assignment: next ID = highest ID currently in [INDEX.md](INDEX.md) + 1. Sequential, never
  reused, even if a tweak is later superseded.
- Every new file gets an index row the same session it's authored. A `CHI-*.md` file with no
  `INDEX.md` row is not addressable and does not count as shipped.

## Shape

Every tweak recipe answers, in order:

1. **Task/goal** — what the tweak actually does, in one line.
2. **Theory** — the conceptual "why," not just the mechanism. What existing signal was
   insufficient, what new evidence type this adds, and why combining them (not replacing either)
   is the right shape. Cross-reference `docs/foundations/parameter_synergies.md` when the theory
   is written up there too — this section here should still stand alone.
3. **Capability used / added** — code refs (file paths, function names), same provenance
   discipline as the generic recipe shape (`../README.md`).
4. **Config** — env vars, DSNs, or other runtime state the tweak needs.
5. **Invocation** — how to actually call it.
6. **Expected output shape** — what a caller should see back, and how to tell it worked.
7. **Validation evidence** — what actually confirmed this works, including honest limits (a
   tweak that overstates its own calibration is worse than one that's candid about being
   diagnostic-only so far).
8. **Rollback** — how to disable it / what happens if its dependency is unavailable.

## Backlog

[BACKLOG.md](BACKLOG.md) — candidates gathered but not yet built, and the gather-then-recalibrate
cadence this directory runs on (operator, 2026-08-18): accumulate genuine tweaks first, then do a
deliberate recalibration pass treating the accumulated tweaks as input for what needs
recalibrating or repopulating, rather than one-tweak-and-ship in isolation each time.

## When it isn't a Chiron tweak

Tuning existing parameters together → [params_combo/](../params_combo/README.md). A single
parameter alone → the generic shape in [../README.md](../README.md). Not yet real, tested code →
not a recipe gap, a feature-theorizing note (`../README.md` "When there's no recipe").
