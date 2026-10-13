# Attribution layer — which module is live

## The live path: `core/attribution/attribution_shared.py`

`runtime/pipeline/analyze.py` is the single execution entry point ("RAW_TEXT -> attribution ->
guards -> SUMMARY"). It calls `attribution_shared.run_attribution_pipeline(...)` unconditionally
— no mode switch, no fallback branch. This is the only attribution pipeline core runs.

Loads `assets/lexicon/curated/A_CORE_STAR_MAP_v0_4_1_3.json` plus the frozen Dict B fallback
(`B0_TOKEN_TO_FAMILY_v0_4_1_4...json` / `B1_SIDE_TO_FAMILY_v0_4_1_4.json`) — real curated
lexicon content, not synthetic data.

## Retired 2026-07-30: `core/attribution/attribution.py` (was "v0.6")

Until this date, this module was the **production default** — selected via
`HESPERIA_ATTRIBUTION_MODE` (default `"v06"`) in `analyze.py`. It loaded
`assets/lexicon/frozen/v0_5_0/dict_a_v06.jsonl` + `family_prior_v06.json` (`v0_5_0` was a symlink to
`assets/lexicon/frozen/v06`).

**That file was synthetic placeholder data — every token a fake string like `access_100_10`,
`area10_217_11`, zero real vocabulary anywhere in it.** The production default had never had a
real calibrated dictionary. Measured against the frozen B0 ground-truth catalog, it scored ~0.2%
family-exact and only ~9.3% area-level (near the ~8.3% random-chance floor for 12 areas) — not
because the pipeline logic was broken, but because the dictionary underneath it was scaffold data
from an unrelated, uncorrelated calibration generation.

Retired as part of severing core from every extension/module and moving the placeholder dictionary
out of the active path:
- `core/attribution/attribution.py` → `core/attribution/_deprecated/attribution_v06.py`
- `assets/lexicon/frozen/v06/` (+ the `v0_5_0` symlink) → `assets/lexicon/frozen/_deprecated/v06/`
- `runtime/pipeline/analyze.py` simplified to call `attribution_shared` unconditionally; the
  `_MODE`/`HESPERIA_ATTRIBUTION_MODE` env-var branch and the now-dead `dict_b` diagnostics block
  it fed (`core.math.dict_b.run_dict_b_pipeline`, only ever reachable in v06 mode) were removed.
- `core.attribution.attribution_shared.load_dict_a_v06()` (an optional fallback loader used by
  `r1_r4_pipeline.py`'s surface-map branch) degrades gracefully when `assets/lexicon/frozen/v0_5_0` is
  absent — returns `{}`, verified this does not break r1_r4.

See `assets/lexicon/frozen/_deprecated/README.md` and `core/attribution/_deprecated/README.md`.

## Also live: `core/attribution/structural.py`

**Not a duplicate of `attribution_shared.py`** — a genuine feature fork. Used by:

- `runtime/pipeline/r1_r4_pipeline.py` (the branch taken when no surface map is present —
  `r1_r4_pipeline.py` deliberately calls both this module and `attribution_shared.py` depending
  on that condition).
- `sphere/pipeline/pipeline_runner.py` (dev/debug-gated, see below).
- `hesperia/engine/multiscale_product_bridge.py`.
- `hesperia/extensions/dynamics/e2e_bridge.py` — note this is an *extension* calling into core
  (the allowed direction), not core depending on the extension.

Its distinguishing feature is an `exclude_landing_sources` guard (PO-11/12: B0-fallback-after-A-
excluded logic, with `excluded_by_guard`/`b_fallback_after_a_excluded` metrics) — this does not
exist anywhere in `attribution_shared.py`.

### Why these two are not merged

`r1_r4_pipeline.py` needs both modules' distinct capabilities simultaneously: surface-map +
span-aware tokenization from `attribution_shared.py`, and the landing-source exclusion guard from
`structural.py`. Merging them without a dedicated feature-parity pass risks silently dropping
one capability. Future reconciliation into one module exposing both is possible but out of scope
here — flagged as a follow-up, not a decision that either module should be deleted.

## Dead, archived: `core/attribution/_deprecated/`

- **`attribution_v06.py`** (formerly `attribution.py`) — retired 2026-07-30, see above.
- **`lexical_loader.py`** — zero importers anywhere except itself. Oldest generation (Spec-20
  v0.3), loaded `A_CORE_STAR_MAP_v0_4_1_1.json` + `B_SURFACE_LEX_FIELD_v1.json`.
- **`attribution_compat.py`** — zero importers anywhere. A deprecation shim whose own docstring
  said "use `core.attribution.structural` instead" — stale advice, since `structural.py` was
  never the sole canonical module either, just one of two live paths.

Kept for reference only, not for reuse. See `docs/archive/ARCHIVE-MANIFEST.md`.

## Related but non-canonical: `sphere/pipeline/pipeline_runner.py`

Not one of the two live attribution modules, but worth naming here since it's easy to confuse
with the real pipeline: `sphere/pipeline/pipeline_runner.py` is gated behind
`HESPERIA_SPHERE_PIPELINE_DEV=1` (raises `RuntimeError` otherwise) and reachable only via a
dev-only debug interface (`sphere/interfaces/debug_interface.py`) and tests.
`tests/test_runtime_spine_integrity.py` already asserts this pipeline is never invoked on the
canonical product path — this doc just makes that enforced-but-undocumented fact readable in
prose.

## `core/domain/pipeline.py` has no relation to any extension/module

README.md calls `core.domain` "the canonical shared KME/domain computation layer" — that's true,
and as of 2026-07-30 it's also fully decoupled from every extension: `run_document()` used to
hard-import `hesperia.extensions.triz.kme_bridge` and call it unconditionally (no flag, no
try/except) — real core→extension coupling, removed. `triz_signals` on `MetricReport` is now
always `None` from core; an integration layer outside core (e.g.
`hesperia/engine/kme/clinical_bridge.py`, which already computed TRIZ signals independently —
core's copy was redundant) may attach an extension-defined object there if it wants one. Domain
and attribution are also still fully decoupled from each other; the only bridge between them is
external, in `hesperia/engine/multiscale_product_bridge.py`.

`core/lexical/analysis_input.py` similarly had a clinical-transcript role-folding branch
(`_clinical_role_line_fold`, importing `hesperia.nlp.transcript_speaker_labels`, flag-gated behind
`HESPERIA_CLINICAL_STRIP_ROLES`) — also removed 2026-07-30. `prepare_structural_analysis_text`'s
generic `policy_mode` parameter and the DLCR text-prep machinery stay (confirmed genuinely
general-purpose — non-clinical values like `FULL_INTERPRETATION`/`STRUCTURE_ONLY` are used
elsewhere); only the clinical-specific bolt-on was excised.

## Quick reference

| Module | Status | Selected by |
|---|---|---|
| `attribution_shared.py` (v0.3.3) | **live, sole core path** | `analyze.py` (unconditional); `r1_r4_pipeline.py` (surface-map branch) |
| `structural.py` | live, r1_r4 non-surface-map + guard | `r1_r4_pipeline.py`, `multiscale_product_bridge.py`, `e2e_bridge.py` |
| `attribution_v06.py` (was `attribution.py`) | dead, archived 2026-07-30 | — |
| `lexical_loader.py` | dead, archived | — |
| `attribution_compat.py` | dead, archived | — |

## Related

- [../TOPOLOGY_INVARIANTS.md](../TOPOLOGY_INVARIANTS.md) — the canon matrix these modules attribute
  text into (now the sphereV genesis taxonomy — see
  [genesis_taxonomy_provenance.md](genesis_taxonomy_provenance.md)).
- `tools/measure_family_area_capacity.py` — measures the live pipeline's logical capacity against
  the frozen B0 ground-truth catalog.
