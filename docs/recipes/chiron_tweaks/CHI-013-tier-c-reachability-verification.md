# CHI-013 — Tier C reachability verification: C1/C2/C3/C5 share one off-path profile, C3's self-flagged claim resolved, C4/C6 confirmed accurate

## 1. Task/goal

First Tier C pass. Tier C is not a Tier-B-style tune-or-hold grind — per the registry's own
framing, none of these 39 candidates reach `/product/interpret` today, and Chiron's scope here is
**verify, then propose wiring if warranted (§5b) — never implement**. This investigation verifies
each pack's actual reachability against the real call graph before any wiring is proposed, same
discipline that caught B1/B6/B7 in Tier B. No code changed.

## 2. C1/C2/C3/C5 — one shared entrypoint, one shared off-path profile

Traced the real consuming functions (not name-collision false leads — see §3) for
Phase3Theta (C1), Phase4Theta (C2), Ξ tension proxy (C3), and Semantic Field v1 (C5):

`hesperia/extensions/dynamics/e2e_bridge.py::run_field_dynamics_e2e_artifact()` is the single
shared entrypoint. Reading its body: it imports and drives `phase1.step_phase1`,
`phase2.step_phase2`, `phase3.step_phase3` (C1), `phase4.compute_l8_clusters`/
`apply_cluster_gravity_to_*` (C2) — all gated behind `field_dynamics_enabled()`
(`HESPERIA_FIELD_DYNAMICS`, the master gate). C3's `xi_proxy.py::apply_xi_to_contradiction_signal`
and C5's `semantic_field_v1.py` attach to the same artifact-generation call chain.

**Grepped every real caller of `run_field_dynamics_e2e_artifact()` specifically** (not just
module-name references, which produced false leads — see §3): the only caller anywhere in the
repository is `runtime/pipeline/run_e2e_all.py` (line 1369) — the "run everything" offline
artifact-generation tool. Confirmed **zero** references from `runtime/api/main.py`,
`runtime/shipping/api_main.py`, `sphere/pipeline/pipeline_runner.py`,
`runtime/services/product_interpret_service.py`, or `hesperia/product/service.py`. This matches
`parameter_catalog.md` §8's own blanket disclosure exactly: "None of the rows below change
anything in `/product/interpret` output today."

Evidence this is real, tested code, not an orphan like B6: `tests/test_field_dynamics_xi_proxy.py`
(10 tests) + `tests/engine/test_semantic_field_v1.py` (10 tests) — **20 passed, 0 failed**.

## 3. False leads corrected before concluding anything

Two module-name grep matches looked like they might change the reachability picture and were
checked precisely before being ruled out — same "verify the exact function, not just the module
name" discipline CHI-011/CHI-012 needed:

- `core/engine/multiscale_product_bridge.py`, `core/engine/sealed_multiscale_stack.py`,
  `hesperia/system/system_seal.py` all import `markers_to_concept_activation` from `e2e_bridge.py`
  — a different, unrelated helper function in the same file, not
  `run_field_dynamics_e2e_artifact()` or any Xi/Phase-theta function. These files never call the
  Field Dynamics artifact generator.
- `core/engine/sealed_multiscale_stack.py` imports `LocalHexMicrophysicsParams` from
  `hex_dynamics.py` — a different dataclass than `HexFieldParams`, and `hex_dynamics.py` itself is
  a separate module from C1's `Phase3Theta` (both deal with "hex" concepts but are distinct code
  paths; not investigated further here — out of this pass's scope).

## 4. C3's own self-flagged claim — resolved

`CANDIDATE-REGISTRY.md`'s C3 row: *"On by default already (`HESPERIA_FIELD_DYNAMICS_XI=1`)
whenever the master gate is on — the one Tier C pack partially live; confirm exact reach before
treating as fully off-path."* This was a real, honest flag from whoever wrote the row — worth
resolving precisely rather than either dismissing or overstating it.

**Resolved**: `field_dynamics_xi_enabled()` reading `HESPERIA_FIELD_DYNAMICS_XI` (default `"1"`,
i.e., on) only matters *once the master `HESPERIA_FIELD_DYNAMICS` gate has already fired* — and
that master gate is checked at the top of `run_field_dynamics_e2e_artifact()`, which (§2) only
`run_e2e_all.py` ever calls. "On by default" describes an env-var default **inside an
already-offline artifact generator**, not reachability from any live product route. C3 has the
**identical off-path profile as C1/C2/C5** — real, tested, gated, offline-artifact-only. The
registry's phrasing wasn't wrong about the env-var default, but the "partially live" framing
overstated what that default actually reaches. Corrected in the registry (§9).

## 5. C4 — confirmed accurate as described

`hesperia/engine/calibration/hspr_field.py` (`compute_hspr`, `hspr_from_observables`,
`source_alignment_kappa`) has **zero real callers** outside its own package `__init__.py`
re-export — matches the registry's framing exactly ("not a runtime param at all... wiring here
means deciding whether to ever run the grid search, not connecting output").

One false lead checked and ruled out by the codebase's own documentation, not by inference:
`core/engine/hspr_index.py::compute_hspr_index()` is called from `sealed_multiscale_stack.py`
(a genuinely live-adjacent module) — but that file's own docstring explicitly disclaims the
naming collision: *"NOT the same as `calibration.hspr_field` (family-field Σ̂/Ê six-observable
HSPR on F)."* Two deliberately, explicitly distinct HSPR-named concepts — the live one is not
C4's target.

## 6. C6 — confirmed accurate, with one added precision

`profiles_v1.json`'s `hex_field_reference` key (`alpha_H=0.12`, `beta_H=0.06`, `gamma_H=0.10`,
`delta_H=0.22`, `dt=0.05`) — **grepped every `.py` file for `hex_field_reference` by name: zero
hits anywhere.** Confirms the registry's claim exactly.

**Added precision, not in the original row**: the *file itself* is not dead — `profiles_v1.json`'s
sibling top-level keys (`alpha`/`beta`/`gamma`/`delta`/`dt`/`epsilon`/`tau`/`clip_mode`, i.e., C5's
params) **are** live, read by `hesperia/engine/calibration_profile.py::semantic_field_params_from_profile()`,
which is called from a genuinely wide set of real modules (`runtime/api/main.py`,
`runtime/shipping/api_main.py`, `core/engine/multiscale_product_bridge.py`,
`core/services/calibration_service.py`, and more). So C6 isn't "an entirely unused config file" —
it's one specific nested sub-object, inside an otherwise-live file, that nothing reads. Worth
stating precisely: the registry's original wording ("not loaded by any live code path") is true
for the hex reference specifically and could be misread as describing the whole file — corrected
in the registry row (§9) to avoid that ambiguity.

Separately noted, not pursued further this pass: `core/engine/hex_dynamics.py::HexFieldParams`'s
own hardcoded defaults (`0.12`/`0.06`/`0.10`/`0.22`) happen to numerically match
`profiles_v1.json`'s dead `hex_field_reference` block exactly — the same "two independent copies,
currently agreeing, no wiring between them" shape CHI-012 found for B1. Whether `hex_dynamics.py`
is itself reachable from a live path is a separate question from C6's — not investigated here,
flagged as a natural follow-up if C1/hex-dynamics wiring is ever taken up.

## 7. What this changes, and what it doesn't

No parameter values changed, no wiring implemented — per spec §5, Chiron proposes for Tier C, does
not implement. What this pass produced: an accurate, verified reachability map for all 6 packs
(down from "assumed accurate except one self-flagged uncertainty" to "traced and confirmed for
every pack, one correction made, one precision added"), so a future Felix/Gena wiring decision (or
a future Chiron feature-theorizing note proposing a specific wiring design) starts from verified
ground truth rather than re-deriving it.

**Registry corrections made** (§9): C3's status line softened from "partially live" to match
C1/C2/C5's off-path framing exactly; C6's wording tightened to name the specific dead key, not the
whole file.

**Not done this pass, deliberately**: no wiring-design proposal written for any pack (that's a
larger, separate feature-theorizing task per pack, better scoped when there's real appetite to
build it — this pass answers "what's actually true today," not "how should it be wired").

## 8. Validation evidence

- Full call-graph trace across `run_e2e_all.py`, `e2e_bridge.py`, `xi_proxy.py`,
  `semantic_field_v1.py`, `hspr_field.py`, `hspr_index.py`, `calibration_profile.py`,
  `profiles_v1.json`, `hex_dynamics.py` — direct reads and greps, not inference.
- `tests/test_field_dynamics_xi_proxy.py` + `tests/engine/test_semantic_field_v1.py`: **20
  passed, 0 failed**.
- §3 thinking-map gate (`cursor-fpf-test-mcp`, `scope="core"`): three evidence items (shared
  entrypoint trace, C3's resolved self-flag, C4/C6 confirmation), `attempt_transition()` →
  **`OutcomeKind.CONTINUE`**, zero validation errors, zero missing evidence.

## 9. Rollback / registry updates made this session

No code rollback needed — nothing changed. `CANDIDATE-REGISTRY.md`'s Tier C section updated: C3's
"why grouped" cell corrected to match C1/C2/C5's confirmed off-path status instead of "partially
live"; C6's cell tightened to specify the dead key precisely, not the whole file.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | Tier C reachability verified across all 6 packs — no code changed, no wiring implemented (spec §5: propose only); one self-flagged claim (C3) resolved, one precision added (C6), C4 confirmed accurate
