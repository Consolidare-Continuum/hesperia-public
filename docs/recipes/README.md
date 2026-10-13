# Recipes

A recipe maps a specific task or application to the Hesperia capability that serves it. Authored
by Chiron (see `AGENTS.md` §Named-owner map; full scope in the brain repo's
`governance/SPEC-ETHAN-CHIRON-HESPERIA-CALIBRATION-ENTITY.md`) whenever a task has a repeatable
shape — this is required output for that work, not optional documentation.

## Shape

Every recipe file answers, in order:

1. **Task** — what the caller actually wants.
2. **Capability used** — which existing Hesperia feature/parameter set serves it, with `grep`-able
   references (file paths, function/class names) per the repo's own provenance discipline
   (`docs/foundations/provenance.md`) — a recipe only cites capability that's running, not
   spec-only.
3. **Config** — the calibration/flag state required (which YAML values, which `DEFAULT_CONFIG`
   toggles, which `runtime/agentic_bridge/flags.py` gates need to be on).
4. **Invocation** — how to actually call it (CLI/API/pipeline entrypoint).
5. **Expected output shape** — what a caller should see back, and how to tell it worked.

## When there's no recipe

If no combination of existing, documented parameters gets a task there, that's not a recipe gap —
it's a feature-theorizing note instead (design proposal, not a workaround), routed through
`inbox.md` → Grace triage like everything else.

## Parameter-combination recipes

A recipe that tunes **more than one parameter at once** for a stated goal gets its own
addressable location, not a flat file here — see [params_combo/](params_combo/README.md) for the
shape and ID scheme, and [params_combo/INDEX.md](params_combo/INDEX.md) for the registry.

## Chiron-tweak recipes

A recipe for a **genuinely usable new capability** (real, shipped, tested code — not tuning
existing parameters) gets its own addressable location too — see
[chiron_tweaks/](chiron_tweaks/README.md) for the shape and ID scheme (`CHI-<NNN>`), and
[chiron_tweaks/INDEX.md](chiron_tweaks/INDEX.md) for the registry.
