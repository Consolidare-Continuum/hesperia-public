# Corner: Release, Seal, and Runtime/Services Discipline (`release/`, `runtime/`, `runtime/services/`, `runtime/shipping/`, `core/diagnostics/determinism.py`)

## Why this corner exists at all

A deterministic engine is a claim, not a fact, until something actively
verifies it on every release. This corner is the mechanism that turns
"deterministic" from an architectural intention into an enforced, evidenced
property of each shipped build. Without it, every other corner's careful
determinism work (frozen dictionaries, fixed weights, YAML-driven rules,
data-driven guards) would be undermined by a release process that could
silently ship a build where one of those guarantees quietly broke.

## Why the release bundle has a fixed, repeated shape across versions
(`manifest.json`, `system_seal.json`, `determinism_report.json`,
`checksums.txt`, `BUILD_PROVENANCE.json`, `final_gate_status.json`)

Each of these artifacts answers a different question that a future auditor
(or the operator, months later) might need answered, and none of them can
substitute for another:

- `manifest.json` / `checksums.txt`: what files, with what hashes, actually
  shipped.
- `system_seal.json` / `final_gate_status.json`: did this build pass the
  guard gates (Sigma/Gamma/Theta and CI checks) at seal time.
- `determinism_report.json`: was determinism actively tested (same input,
  same output) for this specific build, not just assumed from architecture.
- `BUILD_PROVENANCE.json`: what commit, what environment, produced this
  build.

Keeping this shape *identical* across `release/v0.5.0/` through
`release/v0.6.0/` (and the in-progress `release/v0.7.0/RELEASE_SCOPE.md`) is
what lets a reviewer compare any two releases mechanically rather than
re-learning a bespoke release format each time — the seal process itself is
held to the same determinism discipline it's meant to verify.

## Why v0.6.0 introduced a public/prod vs. dev repo split

The 0.6.0 era's commit history shows a deliberate, multi-commit "sanitize for
prod" pass (`chore(prod): remove docs/`, `remove research/`, `remove
governance/`, `corpus-safe verifier`) culminating in twin tags
(`hesperia/rollback-line-20260518`, `hesperia/dev-ready-line-20260518`). This
split exists because a sealed runtime intended for external/product use
should not carry the narrative reasoning trail, internal research corpus, or
calibration dictionary payloads that made the engineering process legible —
those are necessary for *building* the system trustworthily but are not part
of what needs to ship to run it, and shipping them unnecessarily increases
both the audit surface and the risk of leaking corpus/clinical material that
was never meant to be public. The split is the minimal way to keep "how was
this built" (dev repo) and "what actually runs" (prod repo) independently
verifiable.

## Why `runtime/services/` exists as a layer above `core/`/`sphere/`

Engine layers (`core/`, `sphere/`) are pure computation — they should not
need to know about HTTP, environment variables, or deployment concerns.
`runtime/services/` (analysis_service.py, engine_analyze_contract.py,
anchor_map_registry.py, family_graph.py, gcs_lookup.py, hesperia_metric_emit.py,
path_metric.py) exists as the layer that adapts pure pipeline output to
external contracts (the frozen `/analyze` response shape in
`docs/ENGINE-ANALYZE-CONTRACT.md`) and to operational concerns (env-gated
metric emission via `HESPERIA_METRIC_EMIT`/`HESPERIA_GCS_EMIT`). Keeping this
adaptation in its own layer is what let `analysis_service.py` move from
inside the engine to `runtime/` in the v0.4.x→v1.0.0 transition ("fix: e2e
sealing + move analysis_service to runtime for layer boundary") without
touching any core computation — the move was purely a boundary correction,
made possible because the contract layer already existed to absorb it.

## Why `docs/ENGINE-ANALYZE-CONTRACT.md` is explicitly marked "Frozen"

Once an external system (the dev-ready prod line, a deployed API) depends on
the exact shape of `/analyze`'s response, changing that shape silently breaks
every consumer with no warning. Freezing the contract — and requiring the
Python parsing side (`HesperiaPublicSnapshot.from_engine_result`) to raise
`ValueError` on any missing mandatory field — converts "we changed the
contract" from a silent runtime surprise into an immediate, loud failure at
the boundary, which is the only acceptable failure mode once a contract has
external consumers.

## Relationship to neighboring corners

- Verifies the guarantees built by `corners/logic_guards.md` (guard pass/fail
  becomes `system_seal.json`), `corners/calibration.md` (dict pack pinning
  becomes part of `validate_version_consistency`), and the layer contracts in
  `corners/layer_contracts_attribution.md`.
- Is the corner every era documented in `eras/` ultimately answers to: a new
  capability isn't "done" in Hesperia's own terms until it can pass through
  this corner's seal process.

## Documentation seal checklist (added: ISO-grade documentation program)

The same seal discipline this corner applies to code now applies to the standards-mapped
documentation tier at `docs/iso/` and `docs/publication/` (see
`docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`). On every version seal, before `system_seal.json`
is signed:

- Check every `built`-status row in `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md` — if a row's
  `last_verified_against_commit` is behind the commit being sealed, re-verify that document's
  specific claims against current source before the seal proceeds. Do not re-seal on an unverified
  or stale documentation row.
- This is not a new process; it is the existing seal discipline extended to one more artifact
  class, following `docs/foundations/corners/calibration.md`'s own precedent, where a stale example
  pin value was caught and corrected specifically by this documentation program's verification pass
  (`docs/publication/REPRODUCIBILITY_PACKAGE.md` §1).
