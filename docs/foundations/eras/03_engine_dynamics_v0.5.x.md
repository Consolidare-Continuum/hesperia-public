# Era 3: Engine Dynamics v0.5.0 → v0.5.5 — Calibration Becomes Governed (2026-03-18 → 2026-03-30)

## Evidence

```
$ git log v0.4.1_clean..hesperia-engine-dynamics-v0.5.0 --oneline   (17 commits)
af41d9e8 feat: semantic field stack — equations, HCI calibration, ontology matrices, E2E
0e740022 Add field_dynamics engine (phase1-4, state, triz_signal, xi_proxy, e2e_bridge) + tests
04936737 TRIZ engine, KME integration, e2e consolidation (9 stages), product/eval/deploy
4bb8a5c7 TFP testing stack: speaker-aware, transference, temporal, operational analytics,
         normalization, negation, n-grams, calibration, config, ontology registry,
         explainability, logging, corpus, experiments, graph store, benchmark, safety, docs
7722d013 docs: 10+2 topology decision — 10 operational, 2 reserved service areas

$ git log hesperia-engine-dynamics-v0.5.0..hesperia-engine-dynamics-v0.5.1 --oneline
531d6ff2 feat(engine): Tasks 1–11 integration — P_CH, energy, calibration, topology,
          physics validation, system seal, full E2E stack
342f3f00 release: Hesperia Engine Dynamics v0.5.1 (enforcement baseline)
f53569ee release: v0.5.1 sealed audit bundle (final_gate sealed=true)

$ git log hesperia-engine-dynamics-v0.5.1..hesperia-engine-dynamics-v0.5.4 --oneline   (18 commits)
e6b9a228 Ethan task H (H_total): mainline-pin h_total_concepts.json; add
          semantic_dynamics_operator_spec.md
f0eb1f9c TFP calibration: engine, pipeline, schemas, tools, tests, small JSON data
ea591d76 OpenAI calibration: stderr progress, smoke check, batch runners
23f589ae feat: complete modular kernel workflow gates T1-T10
ab1905dd release: seal v0.5.4 deterministic modular pipeline system

$ git log hesperia-engine-dynamics-v0.5.4..hesperia-engine-dynamics-v0.5.5 --oneline
ac872661 feat(engine): wire versioned calibration dict loader
9f554788 feat(product): deliver T11-T20 productization workflow slice
4479c589 release: promote system to v0.5.5
```

## What this era actually is

This is where calibration stops being scattered constants and becomes a governed subsystem with its
own profile bundles, dict pack pinning, and a 20-task workflow gate structure (T1–T10, then T11–T20).
`7722d013`'s "10+2 topology decision" — 10 operational areas plus 2 reserved service areas — is the
origin of the canonical 12-area structure that `area_geometry.yaml` and Sigma's `SIGMA_001
area_vector_len_12` invariant still enforce today; note that two of the twelve areas were from the
start *reserved*, not all operational, a distinction the docstring in `area_geometry.yaml` still
preserves via its "meta reference nodes A6/A12" comment.

`531d6ff2`'s "Tasks 1–11 integration" bundles P_CH (concept→hex projection matrix), energy,
calibration, topology, and physics validation into one sealed system — this is the moment the hex
substrate, topology, and calibration corners are wired together as one validated whole rather than
independent experiments. `ac872661`'s "versioned calibration dict loader" is the direct ancestor of
`VERSION.yaml`'s `active_calibration_dict_pack` pinning field used in every subsequent era.

The parallel "v0.5.x" tag track (`v0.5.0`...`v0.5.5`, distinct from `hesperia-engine-dynamics-v0.5.x`)
ran concurrently and converged before 0.6.0 — both tracks land essentially the same calibration and
topology work under slightly different naming conventions, evidence that this was a single
development effort tagged twice (once per release process, once per engineering milestone) rather
than two competing designs.

## Why this ordering was the minimal right move

Wiring calibration into a single 11-task sealed bundle (rather than calibrating area activation,
topology, and energy independently with no shared seal) prevented exactly the failure mode the
calibration corner's dict-pack-pinning constraint exists to catch: calibrating one subsystem against
a lexicon/topology version that a sibling subsystem had already moved past. Building the modular
kernel's T1–T10/T11–T20 gates as small sequential tasks, each individually sealed
(`ab1905dd release: seal v0.5.4`, `4479c589 release: promote system to v0.5.5`), kept each
increment small enough to validate completely before building the next — the same incremental,
reversible discipline `release/v0.7.0/RELEASE_SCOPE.md` uses for the metric wave four eras later.

See [`corners/calibration.md`](../corners/calibration.md), [`corners/topology_geometry.md`](../corners/topology_geometry.md),
[`corners/hex_substrate.md`](../corners/hex_substrate.md).
