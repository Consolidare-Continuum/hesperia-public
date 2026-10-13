# Corner: Field Dynamics extension (`hesperia/extensions/dynamics/`) — the undocumented ~47-parameter subsystem

**Location:** `hesperia/extensions/dynamics/{state,phase1,phase2,phase3,phase4,xi_proxy,triz_signal,
equations,semantic_field_v1,calibration,matrix_builders,e2e_bridge}.py`,
`assets/calibration/dynamics_parameter_registry.yaml`, `assets/calibration/profiles_v1.json`,
`assets/calibration/semantic_field_equations_v1.json`. Module header self-identifies as **RAD**
("research and development") and cites a canonical spec, `specs/dynamics/ETHAN_SEMANTIC_FIELD_
DYNAMICS_SPEC.md`, that **does not exist anywhere in this repository** — the only trace of this
subsystem's design intent outside the source itself is inline docstrings (`§A.6`, `§H8` section
references to a document nobody can currently open) and one commit-log line in
`eras/03_engine_dynamics_v0.5.x.md` ("Add field_dynamics engine (phase1-4, state, triz_signal,
xi_proxy, e2e_bridge) + tests"). This corner exists to close that gap: every other corner in this
package traces its constants to a checkable spec or canon YAML; this one is documented from the code
itself because that is currently the only source of truth.

## Why this was missing from `parameter_catalog.md` in the first place

The Phase 2 documentation pass (`00_INDEX.md`, `parameter_catalog.md`, this `corners/` directory)
was built by tracing the pipeline that actually reaches `/product/interpret` — L1 through L11,
guards, KME, TRIZ. Field dynamics was never wired into that pipeline (see "Output reachability"
below), so a trace-the-output-path methodology walks straight past it. That is a real blind spot,
not a deliberate scoping choice: the subsystem is real code, has real tests
(`tests/engine/test_semantic_field_v1.py`, `tests/test_field_dynamics_calibration.py`,
`tests/test_dict_calibration_golden.py` neighbors), and is wired into the canonical E2E release
proof (`runtime/pipeline/run_e2e_all.py`) as an optional 20th artifact. "Not on the product path
today" is not the same as "doesn't exist" or "can't affect an output someone reads."

## What it is: four phases modeling four resolution levels, opt-in, each with its own gate

`state.py` defines four frozen dataclasses — `Phase1Theta` (L6 area / L7 pressure / L9 stability,
9 fields), `Phase2Theta` (L5 family, 9 fields), `Phase3Theta` (L4 hex-cell active subgraph, 9
fields), `Phase4Theta` (L8 cluster gravity, 3 fields) — each a named, symbol-labeled (`λ_a`, `γ_f`,
`β_x`, `θ_c`, …) constant set with defaults duplicated in
`assets/calibration/dynamics_parameter_registry.yaml`. Every phase decays a state vector toward a
new injected value, subtracts a contradiction-pressure term, and (from Phase 2 up) blends in the
level below via a mixing weight (`area_hit_weight`, `hex_hit_blend`) — the same
decay/inject/diffuse/pressure-penalize shape recurs at every level, which is why the four
dataclasses read as one family of 30 constants rather than four unrelated designs.

Layered on top: `xi_proxy.py` (Ξ tension proxy — `xi_scale`, `xi_kme_weight`, and two **hardcoded,
not-env-configurable** blend constants, `0.35`/`0.65`, inside the boost formula
`boost = xi_scale · (0.35·global_tension + 0.65·per_area_tension)`); `triz_signal.py` (feeds TRIZ
contradiction rows into the same signal); `calibration.py`'s `compute_hspr_calibration_index` (6
weighted components + 1 saturation constant, an internal grid-search fitness function — a
calibration score *about* this subsystem, not a runtime output parameter); and a fully separate
canonical-equations module, `equations.py`/`semantic_field_v1.py`
(`alpha, beta, gamma, delta, mu, dt, epsilon, tau, resistance_uniform, production_clip,
signed_source_experimental` — 11 constants, mirrored in `assets/calibration/semantic_field_equations_v1.json`).

**These two families of "alpha/beta/gamma/delta" are not the same parameters** despite sharing
Greek-letter names with each other and with the Core Math Contract's `alpha`/`k_*` constants
already in `parameter_catalog.md` §3 — the Phase-N thetas are heuristic ODE-style mixing weights;
the `SemanticFieldParamsV1` set are physical diffusion-equation coefficients
(`E = (α/2)FᵀLF + (β/2)FᵀRF + (γ/2)FᵀCF − δSᵀF`). Same letters, three unrelated constant sets
(Core Math Contract, Phase-N Theta, Semantic Field v1) — a naming collision worth flagging the same
way `provenance.md` flags the KSI/KSI-Inspector collision.

`assets/calibration/profiles_v1.json` formerly carried a `hex_field_reference` block
(`alpha_H, beta_H, gamma_H, delta_H, dt`) — a fourth near-namesake set never loaded by any code
path. **Removed CHI-014-02** (Felix); sibling top-level profile keys remain live for Semantic Field
via `calibration_profile.py`.

Total distinct named constants across the subsystem: **~42** live/off-path (30 Phase-N theta fields
+ 4 xi-proxy + 7 HCI + 11 semantic-field-v1 + 1 DLCR `dlcr_alpha=0.22`) — the five dead hex-reference
names are retired hygiene, not a live count.

## Output reachability — the part that actually matters for how to read this corner

This is not one on/off subsystem; it is a stack of independently-gated env flags, and the defaults
are not uniform:

| Env var | Default | What it gates |
|---|---|---|
| `HESPERIA_FIELD_DYNAMICS` | **off** | Master gate. Off ⇒ nothing below runs, no artifact written. |
| `HESPERIA_FIELD_DYNAMICS_PHASE2` / `_PHASE3` / `_PHASE4` | **off** each | L5/L4/L8 phases; Phase 1 (L6) runs alone if only the master gate is set. |
| `HESPERIA_FIELD_DYNAMICS_XI` | **on** (default `"1"`) | Ξ tension boost to `contradiction_signal_12` — live whenever the master gate is on, unless explicitly disabled. |
| `HESPERIA_FIELD_DYNAMICS_TRIZ` | **on** | TRIZ-row contradiction signal feed; off ⇒ zero signal. |
| `HESPERIA_FIELD_DYNAMICS_XI_KME` | off | KME-full-graph blend into Ξ (`xi_kme_weight=0.55`). |
| `HESPERIA_FIELD_DYNAMICS_DLCR` | off | Lexical-concept blend (`dlcr_alpha=0.22`) into family injection. |
| `HESPERIA_SEMANTIC_FIELD_EQUATIONS_V1` | off | The entire `equations.py`/`semantic_field_v1.py` constant set — separate research bundle, separate output key. |

Even fully enabled (master + all phases + Ξ + TRIZ), the artifact this subsystem produces
(`run_output_e2e_field_dynamics.json`) is written by `run_e2e_all.py` as an **optional 20th file
alongside** the ~19-file canonical release bundle — `runtime/services/product_interpret_service.py`
(the code behind `/product/interpret`) never imports or reads it. Confirmed by grep: zero references
to `field_dynamics` anywhere under `runtime/services/` or the product API. **This subsystem currently
affects nothing an operator sees through the governed product surface.** It is live, tested,
E2E-wired, environment-gated infrastructure that has no path to an end user today — the honest
description is "shipped instrument, not yet connected," not "dead code" and not "part of the output."

If that connection is ever made — say, a future phase feeding `contradiction_signal_12` or
`stability_index` back into the L1–L11 chain — every constant in this corner becomes a genuine
output-shaping parameter overnight, and this corner (plus `parameter_catalog.md` §8) is the
inventory to update at that point, not to re-derive from scratch.

## Relationship to neighboring corners

- Distinct from `corners/physics_dynamics_coupling.md`'s in-pipeline physics (mean-field decay
  ODEs, Chapman-Kolmogorov propagation) — that corner covers constants that *do* reach
  `/product/interpret` today (Core Math Contract, `core/math/core_math.py`); this corner covers a
  structurally similar but currently disconnected parallel system.
- `corners/calibration.md` covers the *governed process* for calibrating canon thresholds (offline
  LLM-assisted, frozen, pinned in `VERSION.yaml`). This subsystem's own `calibration.py` (HSPR
  Calibration Index, grid search) is a narrower, self-contained instance of that same discipline,
  scoped only to Phase-N theta tuning — it does not (yet) feed the pinned canon calibration pack.
- `corners/triz_extension.md` is read-only against the L1–L11 chain by design; `triz_signal.py`
  here reuses TRIZ contradiction rows as an *input* to field dynamics, which is a legitimate
  one-directional consumption (TRIZ → field dynamics), not a violation of TRIZ's own read-only
  boundary against the sphere pipeline.
- `EXTENSION_STATUS.yaml` (referenced in `eras/05_sealed_0.6.x.md`) classifies extensions by
  product surface (`none`/`internal`/`optional`) for release-scope purposes — this corner's
  "output reachability" finding is the concrete answer for where `hesperia/extensions/dynamics/`
  sits in that classification: `internal`, not `optional`, until a governed decision routes its
  output into the product surface.
