# CHI-006 — B6 diagnostic rule thresholds: unwired, not a tunable pack (finding + fix proposal, not implemented)

## 1. Task/goal

Second Tier B pack (registry's recommended order: B8 done → **B6** next, "CHI-003-adjacent,
already-warm context"). Expected this to mirror CHI-005's shape: review 11-ish live thresholds,
run the toolchain, hold or tune. Instead traced the actual call graph before touching anything
(per §3 discipline — verify reachability, not just YAML presence) and found the entire pack
describes code with **zero live callers anywhere in the repository**. This changes the
deliverable: not a tune-or-hold verdict, but a wiring-gap finding + registry/catalog correction,
same shape as CHI-002/CHI-004.

## 2. What the registry/catalog claim vs. what the code actually does

`CANDIDATE-REGISTRY.md`'s Tier B header: "All of these are on the real `/product/interpret`
output path today — a change here changes what a caller sees." `parameter_catalog.md` §4
("Diagnostic rule thresholds... what the output is allowed to call itself") lists 11 rows sourced
from `assets/specs/canon/diagnostic_rules.yaml`, consumed by three detector modules in
`sphere/diagnostics/` (`anomaly_detector.py`, `monotony_detector.py`, `instability_detector.py`,
orchestrated by `diagnostics_runtime.py::run_diagnostics()`).

**Traced the actual call graph, not assumed it from the YAML's existence:**

- `grep` across every `.py` file in the repo (production *and* tests) for
  `detect_structural_monotony`, `detect_structural_anomalies`, `detect_rhetorical_instability`,
  `run_diagnostics`, `sphere.diagnostics`, `sphere import diagnostics` — every hit is inside
  `sphere/diagnostics/` itself (the module re-exporting its own functions) or
  `docs/brain-export/colombo/hesperia-wiki/tools/generate_wiki.py` (the wiki *generator*, which
  documents the code, not a caller of it). **Zero test files reference any of these functions or
  the module at all** — not even a standalone unit test exercising the detector logic directly.
- Read `runtime/services/product_interpret_service.py::run_product_interpret()` — the function
  literally backing `POST /product/interpret`
  (`runtime/shipping/api_main.py:413-430`, the real shipping route, confirmed by reading the
  route registration directly). It imports `sphere.router.ground_truth` and
  `sphere.router.pre_llm_compiler` — **no reference anywhere to `pipeline_runner`,
  `sphere.pipeline`, `sphere.logic`, `sphere.diagnostics`, or `diagnostic_rules`.**
- `sphere/diagnostics/`'s single git-blamed commit (`802efcf9`, "Add testing framework, interface
  layer, structural geometry, diagnostics") landed the module and its YAML together, complete and
  internally correct, but nothing in that commit or any since wired a caller in.

**A structurally similar, but separate and genuinely live, system exists** — found while checking
whether this was really unreachable everywhere, not just from `/product/interpret`:
`sphere/logic/rule_engine.py`'s Layer-9 (`compute_logic_metrics()`), driven by a *different* spec
file (`assets/specs/canon/logic_rules.yaml`, declarative rule conditions, "no thresholds in
Python" per its own header comment), **is** wired live —
`sphere/pipeline/pipeline_runner.py::run_pipeline()` calls it directly (line 322), and
`run_pipeline()` is in turn called by `hesperia/product/service.py::run_product_profile()`, which
backs `POST /product/tfp`, `/product/fingerprint`, `/product/llm-audit` (`runtime/api/main.py`) —
**a different product surface than `/product/interpret`**. 8 test files exercise `sphere/logic/`
(`tests/logic/*.py`, `tests/layers/test_logic_layer.py`) — genuinely tested, genuinely live, just
not the same module the registry/catalog point at for B6.

**The two systems overlap conceptually but diverge numerically** — not a simple duplicate:

| Concept | `diagnostic_rules.yaml` (B6, dead) | `logic_rules.yaml` (Layer-9, live) |
|---|---|---|
| Low entropy → monotony | `entropy_threshold = 0.35` | `RULE_001`: `entropy < 0.35` — **same value** |
| High curvature → instability | `curvature_threshold = 1.20` | `RULE_003`: `curvature > 1.20` — **same value** |
| Low coverage | `coverage_threshold = 0.20` | `RULE_004` `low_coverage`: `coverage < 0.60` — **different** |
| Low stability | `low_stability_threshold = 0.15` | `RULE_005` `volatile_movement`: `stability_index < 0.25` — **different** |
| `ultra_sparse_coverage_threshold`, `excessive_jump_threshold`, `transition_concentration_threshold`, `dominant_area_share_threshold`, `unique_areas_max`, `severe_curvature_threshold`, `severe_jump_rate_threshold`, `stability_high_threshold` | present | **no counterpart at all** |
| `GOVERNANCE_BIAS`, `LOW_COVERAGE`, `VOLATILE_MOVEMENT` diagnostic codes | no counterpart | present |

So even where the concepts line up (entropy, curvature), the *values happen to match* — likely
copied when `logic_rules.yaml` was authored — but they are two independently-editable files with
no mechanism keeping them in sync, and most of B6's named params (8 of 13) have no live analogue
anywhere.

## 3. Secondary finding — catalog/registry undercount

Neither `parameter_catalog.md` §4 nor `CANDIDATE-REGISTRY.md`'s B6 row lists
`stability_high_threshold`, but it is real, live-in-source (used at
`monotony_detector.py:50,88,114` for the `STRUCTURAL_MONOTONY_LOW_DIVERSITY` diagnostic) — same
unreachability status as the other 11, just missing from both docs' listings. Doesn't change the
core finding (still 100% unreachable), but the accurate count for this pack is **13 named
constants across `diagnostic_rules.yaml`, not 11**.

## 4. Validation evidence

- Full call-graph trace above (grep + direct read, not inference from YAML presence) — same
  discipline as CHI-002's marker_index trace and CHI-004's dead-return-field trace.
- `tests/logic/` + `tests/layers/test_logic_layer.py` (the *live* system's coverage, run as
  contrast evidence that this repo does correctly wire and test comparable code when it means to):
  **26 passed**, 0 failed.
- `sphere/diagnostics/` has no tests to run — confirmed absence is itself part of the finding, not
  an omission in this investigation.
- §3 thinking-map gate (`cursor-fpf-test-mcp`, `scope="core"`): three evidence items (call-graph
  trace, parallel-system divergence table, catalog undercount), `attempt_transition()` →
  **`OutcomeKind.CONTINUE`**, zero validation errors, zero missing evidence.

## 5. Proposed fix (not implemented — spec only, per Chiron's scope boundary)

This is a real architecture/product-surface decision, not a documented-parameter toggle Chiron can
resolve unilaterally (spec §5: "may propose, not implement alone... new layer logic" — deciding
which system is canonical is exactly that). Three honest options, not a recommendation to pick one
without Felix/Gena/operator input:

1. **Wire `sphere/diagnostics/run_diagnostics()` into `/product/interpret`** — the registry's
   original intent. Needs: a call site in `product_interpret_service.py`, a decision on whether it
   runs alongside or instead of Layer-9's rule engine on the *other* product surfaces (risk of two
   diagnostic systems disagreeing on the same session), and real-session validation once wired
   (the same toolchain CHI-005 proved on B8 would apply here, but only after wiring — there's
   nothing to validate against real output before that).
2. **Retire `sphere/diagnostics/`** — if Layer-9's `logic_rules.yaml` is meant to be the one
   canonical diagnostic-rule system going forward, `sphere/diagnostics/` (complete, tested-never,
   called-never) is dead weight, similar in kind to Tier C's C6 (`profiles_v1.json`) — a
   deprecation candidate, not a calibration one. `parameter_catalog.md` §4 and
   `CANDIDATE-REGISTRY.md`'s B6 row would need rewriting to point at `logic_rules.yaml` instead
   (with `stability_high_threshold` either genuinely dropped or ported into a new
   `logic_rules.yaml` rule if the LOW_DIVERSITY case is still wanted).
3. **Reconcile the two files** — bring `logic_rules.yaml`'s divergent values (`coverage_threshold`
   0.60 vs 0.20, `low_stability_threshold` 0.25 vs 0.15) and missing rules into alignment with
   `diagnostic_rules.yaml` (or vice versa) as a single source of truth, then wire whichever module
   is kept into every product surface consistently. Highest-effort option, but the only one that
   makes both docs' "what the output is allowed to call itself" framing true everywhere at once.

Routing this to `inbox.md` → Grace triage per the same rule as CHI-002/CHI-004, not a Chiron
merge.

## 6. Config

No change made. Both `diagnostic_rules.yaml` and `logic_rules.yaml` remain exactly as found.

## 7. Invocation

N/A — spec/finding only, nothing to invoke yet. Once a wiring decision is made, CHI-005's
toolchain (real `--with-triz`/`--with-topology` session run + `calibration_release_gate.py` +
pytest) is the validation path to reuse.

## 8. Expected output shape (once a decision is made and implemented)

Depends entirely on which of the three §5 options is chosen — deferred to that decision, not
speculated here.

## 9. Rollback / registry correction made this session

No code rollback needed (nothing changed). `CANDIDATE-REGISTRY.md`'s B6 row updated to flag this
finding instead of "Not started" (which implied "ready to tune," which it isn't) — see the
registry diff in the same commit as this file. Wiki's five `LIVE_FULL — running in production
path` entries for these params (`entropy_threshold (monotony)`, `coverage_threshold (monotony)`,
`excessive_jump_threshold`, `ultra_sparse_coverage_threshold`, `transition_concentration_threshold`)
are inaccurate for the specific claim "running in production path" — reported to Colombo via
`inbox.md` per spec §8a ("Chiron's role is reporting status-change evidence... not editing the
generator"), not corrected directly.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | B6 traced end-to-end, found unwired everywhere (not just off one path) — finding + fix proposal, routed to triage, not implemented
