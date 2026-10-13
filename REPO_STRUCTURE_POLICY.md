# Hesperia — Repo Structure Policy

**Root is a closed set.** 15 real directories + 1 symlink. Machine-readable companion:
[`repo_refresh_manifest.yaml`](repo_refresh_manifest.yaml). Enforced by
[`tests/architecture/test_root_structure_locked.py`](tests/architecture/test_root_structure_locked.py) —
CI fails the moment a 16th directory appears at root without this document and the manifest
being updated in the same change. That is deliberate, not an accident of tooling: every entry
below earned its place by being referenced from `docs/iso/ARCHITECTURE_DESCRIPTION.md`'s own
`core`/`sphere`/`runtime` viewpoint or by genuinely having nowhere else to nest. A `mkdir` at
root that isn't one of these 15 is a bug, not a feature.

This document exists because two 2026-07-31 root-cleanup passes (moving `hesperia/engine`'s
generic code into `core/engine/`, then folding `configs/`, `data/`, `lexicon/`, `schemas/`,
`specs/`, `scripts/` into `assets/`/`tools/`) took root from 27 real directories down to 15.
Nothing here should ever require that kind of pass again — the point of formalizing the count
is that going back up is now a visible, deliberate decision, not clutter that accumulates one
convenient `mkdir` at a time.

## The three code roots (never merge; see `docs/iso/ARCHITECTURE_DESCRIPTION.md` §2)

| Dir | Why it's top-level |
|---|---|
| **`core/`** | The sealed, module-agnostic computational substrate — primitive math, attribution, topology invariants, the canonical `analyze_engine()` entrypoint, and (as of 2026-07-31) the generic orchestration/physics backbone graduated from `hesperia/engine/`. Zero relation to any one module's domain semantics (no TFP, no clinical, no TRIZ) — that boundary is what makes `core/` reusable across every orchestration context instead of just one. |
| **`sphere/`** | Layer-stack orchestration and interpretation — the L1–L10 pipeline, calibration, diagnostics, the FPF bridge (Layer 11), USF generation. Consumes `core/` primitives; must not implement its own math or reach into `runtime/` (both enforced by `tests/architecture/`). |
| **`runtime/`** | The boundary layer to external contracts — the governed HTTP/CLI surfaces, the canonical E2E runner, shipping build output. Consumes `sphere/`+`core/`; owns sequencing correctness for nothing, only consumption. |

Collapsing these three under one parent (e.g. `src/`) was explicitly considered and rejected
2026-07-31: it would contradict the architecture doc's own stated rationale for keeping them
independently testable, and — unlike every other consolidation this policy documents — would
require rewriting Python import paths across the entire codebase rather than just file-path
references.

## Module / research surfaces

| Dir | Why it's top-level |
|---|---|
| **`hesperia/`** | Module-specific semantics that `core/` explicitly has zero relation to: TFP math and calibration, concept dictionaries, KME (clinical/TRIZ-coupled), the pluggable module registry's actual implementations (`hesperia/modules/`), NLP, ontology, the product/business layer, system identity/versioning. The "leave behind" side of every core-graduation pass this session. |
| **`research/`** | Non-product research surface: `clinical_tfp` (experimental, `product_surface: none` per `EXTENSION_STATUS.yaml`), TRIZ evaluation/baselines, ontology-version experiment running. Consumed by `hesperia/product/release_gate.py` and `runtime/pipeline/run_e2e_all.py` as benchmark tooling, but never shipped as product surface itself. |

## Data / reference assets

| Dir | Why it's top-level |
|---|---|
| **`assets/`** | The single home for static reference data: calibration bundles, `lexicon/` (curated + frozen dictionaries — the default assets root for ~70 call sites across the whole engine), `schemas/` (JSON Schema contracts), `specs/` (canon specs, calibration examples, validation thresholds), `topology/` (adjacency/hex-weight matrices), `config/` (pipeline config), brand, matrices, public schema, artifacts, reserve. As of 2026-07-31 this absorbed what used to be five separate root directories (`configs/`, `data/`, `lexicon/`, `schemas/`, `specs/`) — none of them were Python import roots, so nothing stops new reference-data categories from nesting here too instead of spawning a new root directory. |

## Dev/test/tooling

| Dir | Why it's top-level |
|---|---|
| **`tests/`** | The pytest suite. Standard convention; stays at root regardless of size (149 top-level entries) because every Python testing tool expects it there. |
| **`tools/`** | CLI scripts: calibration pipelines, validation/audit/build scripts, the dev-test diagnostic battery, release tooling, the openai-calibration scripts and shell-verification scripts absorbed from root 2026-07-31. If it's a script you run by hand or from CI rather than a library the engine imports, it lives here. |
| **`examples/`** | Worked examples and demo output (including `extensions/triz_demo/`) — read-only illustrations, not tests and not tooling. |

## Docs, release, build plumbing

| Dir | Why it's top-level |
|---|---|
| **`docs/`** | All documentation: foundations (theory, provenance, parameter catalog), the ISO/IEC/IEEE 42010 architecture description set, publication/awareness material, the brain-repo export/link mirrors, archive. |
| **`release/`** | Versioned release audit bundles and manifests (`v0.5.0` through `v0.7.0`) — the actual sealed-release evidence trail, distinct from `docs/` narrative. |
| **`requirements/`** | Pip requirement files split by deploy surface (`api.txt`, `runtime.txt`, `shipping.txt`, `cobalt.txt`, `calibration.txt`, `output_views.txt`, ...) rather than one monolithic file, because different surfaces (the sealed shipping image vs. the calibration tooling vs. `output_views`'s Django app) intentionally pull different dependency sets. |
| **`output_views/`** | A separate Django project (hex matrix viewer, segment tooling) — has its own `manage.py`, its own `requirements/output_views.txt`, its own app structure. Top-level because it is genuinely a distinct sub-application, not a package the main engine imports. |

## Generated (gitignored-in-spirit, present for path stability)

| Dir | Why it's top-level |
|---|---|
| **`outputs/`** | Runtime-generated report output. Present (with `.gitkeep`) so code that writes there doesn't need to `mkdir -p` defensively. |
| **`tmp/`** | Scratch space for tooling. Same reasoning. |

## The symlink

| Path | Why it exists |
|---|---|
| **`spec`** → `assets/specs/canon` | A stable shorthand used as a docstring citation convention across ~12 files (`"""Spec: spec/hex_family_bridge.md"""` etc.) — repointing this one symlink on a future move keeps every one of those citations correct without touching each file. Not a real directory; doesn't count against the 15. |

## Adding a 16th directory

There isn't a process that makes this routine — that's the point. If something genuinely needs
a new top-level home:

1. Check it isn't better served by nesting inside `assets/` (data), `tools/` (a script),
   `docs/` (documentation), or one of the three code roots first. Most things are.
2. If it truly needs to be new, update this document (a new row, with the same "why top-level,
   not nested" justification every existing row has) and `repo_refresh_manifest.yaml` in the
   same change that creates the directory.
3. `tests/architecture/test_root_structure_locked.py` will fail until both are updated —
   that failure is the mechanism, not a bug to work around.

SIGNED: Developer (Felix) | Claude Code context | 2026-07-31 | root structure formalization after the configs/data/lexicon/schemas/specs/scripts consolidation
