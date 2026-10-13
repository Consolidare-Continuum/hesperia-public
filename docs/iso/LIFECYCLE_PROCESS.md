# Software life cycle process model (ISO/IEC/IEEE 12207 form)

Hesperia already runs a real, evidenced life-cycle discipline — the era/release/seal process
documented in `corners/release_governance.md` and `corners/release_seal.md`. This document maps
that existing discipline onto 12207's named process categories. It formalizes vocabulary; it does
not introduce a new process the project doesn't already run.

## 1. Development process

Each capability moves through the same discipline every `eras/*.md` document narrates: a gap is
identified, a minimal addition is made, and the addition is not "done" in the project's own terms
until it passes the seal process below (`corners/release_governance.md`: "a new capability isn't
'done' in Hesperia's own terms until it can pass through this corner's seal process").

**Live example as of this writing**: the three `fpf_bridge_v7_2`–`v7_4` specs
(`docs/foundations/eras/08_fpf_bridge_v7_2_v7_4.md`) are all in the "minimal addition made, not yet
sealed" state simultaneously — code shipped and tested against synthetic input, every new capability
flag-gated off, explicit ratification-pending status on each spec's own header, with the specific
next-owner (Ethan, Sophia, Abelard, Colombo, or Olga) named per open item rather than left implicit.
This is the process this section describes, not an exception to it.

## 2. Verification and validation process

- **Verification** (did we build it right): the guard triad — Sigma (static shape), Gamma (dynamic
  execution order), Theta (governance eligibility) — `corners/guards.md`.
- **Validation** (did we build the right thing): calibration against labeled corpora
  (`specs/canon/activation_calibration.yaml`'s own comment: "Tune after validation on 20–50 TFP
  transcripts," `corners/calibration.md`), and the shadow-run acceptability gate as an ongoing
  perturbation-robustness check (`corners/guards.md`).

## 3. Configuration management process

`VERSION.yaml` is the single source of truth every component version, calibration pin, and pipeline
version must agree against (`corners/release_governance.md`). `tfp_module_v1.pinned_calibration_dict_pack`
must match `defaults.active_calibration_dict_pack` "for mainline" — an explicit, enforced
cross-check, not a convention.

## 4. Release/deployment process — the release bundle

A fixed, repeated artifact shape across every version (`corners/release_seal.md`):

| Artifact | Question it answers |
|---|---|
| `manifest.json` / `checksums.txt` | What files, with what hashes, shipped |
| `system_seal.json` / `final_gate_status.json` | Did this build pass the guard gates (Sigma/Gamma/Theta) and CI checks at seal time |
| `determinism_report.json` | Was determinism actively tested for this specific build, not assumed from architecture |
| `BUILD_PROVENANCE.json` | What commit, what environment, produced this build |

Keeping this shape identical across `release/v0.5.0/` through `release/v0.7.0/` is what lets a
reviewer compare any two releases mechanically instead of re-learning a bespoke format each time —
the seal process is held to the same determinism discipline it verifies (`corners/release_seal.md`).

## 5. Infrastructure/environment management — the dev/prod split

The 0.6.0 era introduced a deliberate public/prod-vs-dev repository split (documented commit
sequence: `chore(prod): remove docs/`, `remove research/`, `remove governance/`, a corpus-safe
verifier; twin tags `hesperia/rollback-line-20260518` / `hesperia/dev-ready-line-20260518`,
`corners/release_seal.md`). This exists so a sealed runtime intended for external use doesn't carry
the narrative reasoning trail or proprietary calibration/corpus payloads that made the engineering
process legible internally — necessary for *building* the system trustworthily, not part of what
needs to *ship* to run it.

## 6. Boundary/adaptation layer — `runtime/services/`

`core/`/`sphere/` are pure computation and should not need to know about HTTP, environment
variables, or deployment concerns. `runtime/services/` is the layer that adapts pure pipeline
output to external contracts (`docs/ENGINE-ANALYZE-CONTRACT.md`'s frozen `/analyze` shape) and to
operational concerns (env-gated metric emission). This boundary is what let `analysis_service.py`
move from inside the engine to `runtime/` during the v0.4.x→v1.0.0 transition without touching any
core computation (`corners/release_seal.md`).

## 7. Change control for frozen contracts

`docs/ENGINE-ANALYZE-CONTRACT.md` is explicitly marked "Frozen": once an external system depends on
`/analyze`'s exact response shape, silently changing it breaks every consumer with no warning.
`HesperiaPublicSnapshot.from_engine_result` raises `ValueError` on any missing mandatory field —
converting "we changed the contract" from a silent runtime surprise into an immediate, loud failure
at the boundary, the only acceptable failure mode once a contract has external consumers
(`corners/release_seal.md`).

## 8. This process model's own maintenance

This document is a **mapping**, not a second process — if `corners/release_governance.md` or
`corners/release_seal.md` change, this document's section headers stay the same (they're 12207's
category names) but the content under them must be re-checked against the updated corner doc in the
same commit. Registered in `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`.

## Addendum: documentation seal checklist (LTS mechanism)

Per this documentation program's own plan, on every version seal (before `system_seal.json` is
signed), add one check to the existing seal process:

- Confirm `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md` has no row whose
  `last_verified_against_commit` predates a change to the artifact it cites. If one exists,
  re-verify that row's document against current source before the seal proceeds — the same
  discipline that caught the field-dynamics documentation gap this program started from
  (`corners/field_dynamics.md`).

This addendum belongs in `corners/release_seal.md` itself once this documentation program is far
enough along to be part of the standard seal checklist — noted here first so the requirement is not
lost, formal placement is a Phase E follow-up.

## Navigation

← [`docs/README.md`](../README.md) (start here) · [`DOCUMENTATION_TRACEABILITY_MATRIX.md`](DOCUMENTATION_TRACEABILITY_MATRIX.md) (master registry)
Related: [`../foundations/corners/release_seal.md`](../foundations/corners/release_seal.md) (this document's addendum now lives there too) · [`../foundations/corners/release_governance.md`](../foundations/corners/release_governance.md) (§3's source) · [`QUALITY_MODEL.md`](QUALITY_MODEL.md) (Maintainability/Reliability rows this process produces evidence for)
