# CHI-002 — TFP batch-pipeline KME: wrong grain default + missing single-token marker index

## 1. Task/goal

Two real, confirmed gaps in how `runtime/pipeline/run_tfp_file_pipeline.py` (the offline batch
tool behind `tools/gena_tfp_bundle_run.py`, used for every real-session TFP run this and prior
sessions have done) invokes KME (`07_session_kme.json`) for TFP sessions:

1. Every historical TFP batch run has computed KME's comparability primitives/derived metrics at
   `area_math_grain=12` (core default) instead of TFP's own `area_math_grain=10`.
2. KME's single-token/n-gram-string concept-marker channel is silently disabled for every TFP
   batch run (phrase-based detection and area/family attribution both work correctly).

Both were first suspected as one big "KME is broken for TFP" problem; traced precisely, they are
two small, separately-scoped, separately-fixable gaps — narrower than the initial read.

## 2. Theory / root cause

**Gap 1 — grain**: `core/projection/area_math_grain.py::classify_area_math_grain()` resolves the
active grain from `HESPERIA_AREA_MATH_GRAIN` (explicit env, canonical switch, not a second
geometry constant — the sealed `AREAS=12` lock is untouched either way) with a **default of 12**
when unset. The live `/analyze` service (`:18880`/`:18881`) gets grain=10 for TFP automatically via
`runtime/shipping/analyze_profile.py::apply_analyze_profile_defaults(profile="tfp")`, which sets
`HESPERIA_AREA_MATH_GRAIN=10` as one of several `tfp`-profile defaults. **`run_tfp_file_pipeline.py`
never calls `apply_analyze_profile_defaults()`** — confirmed via `grep`, zero references — so every
invocation of the batch tool that doesn't *manually* export `HESPERIA_AREA_MATH_GRAIN=10` gets the
core default of 12. Checked this session's own runs and the historical `tfp_gena_*` output
directories from 2026-08-18/19: none of them set this var. `core/projection/apply_public_projection()`
(called on the KME body, `run_tfp_file_pipeline.py:939`) stamps whatever the classifier currently
resolves onto the output — so `"area_math_grain": 12"` in every existing TFP KME artifact is an
accurate report of what was actually configured, not a bug in the projection/stamping code itself.
The ontology backing the domain graph (`hesperia/ontology/dictB/concept_nodes.yaml`) is genuinely
10-area (verified: `grep -oP 'area: A\d+' | sort -u` → exactly A1–A10) — so grain=12 really is the
wrong shape for TFP's own concept space, not a false alarm.

**Gap 2 — marker_index**: `run_session_kme_pipeline()` (`hesperia/engine/kme/clinical_bridge.py:622`)
calls `analyze_session(text, embedding=embedding, **kwargs)` with no `marker_index`,
`concept_to_area_family`, or `phrase_index` passed — and `run_tfp_file_pipeline.py`'s own call site
(`run_session_kme_pipeline(t, source_id=sid)`, line 938) passes nothing beyond text/session_id
either. Traced each parameter's fallback in `hesperia/nlp/session_parser.py::analyze_session()`
individually, not assumed as a block:
- `phrase_index` → `_get_phrase_index()` → `hesperia.ontology.dictA.build_phrase_marker_index()`
  — **has a real ontology-based fallback**, correctly TFP-aware.
- `concept_to_area_family` → traced one level deeper into
  `hesperia/nlp/invariant_activation.py::build_invariant_activation()` (line 211):
  `af = concept_to_area_family if concept_to_area_family is not None else build_concept_to_area_family()`
  — **also has a real ontology-based fallback**, correctly TFP-aware.
- `marker_index` → **no fallback anywhere in `analyze_session()`'s call chain**. Stays `None`.
  `detect_markers(normalized, marker_index=None, ...)` for the single-token/n-gram-string channel
  — the phrase-based channel is explicitly documented as priority (`analyze_session()`'s own
  docstring: "Фразовые маркеры (приоритет)"), so this is a real but secondary coverage gap, not
  total signal loss. **Correction to an earlier same-session claim**: initially read this as
  possible near-total activation failure (based on one session's `CI=9.8e-05`) before finishing the
  trace — that reading overstated it. Two of three matching channels are intact via ontology
  defaults; only the supplementary single-token layer is missing. `hesperia.ontology.dictA` already
  has the exact function needed: `build_marker_to_concepts()` (also used by
  `session_parser.py::_get_merged_marker_index()`, an existing, ready-made combined index).

## 3. Proposed fix (not yet implemented — spec only, per Chiron's own scope boundary: this is
pipeline call-site wiring, not a documented-parameter toggle, so it's a proposal, not a Chiron
unilateral merge)

Both fixes are small, targeted, and independent — no sealed-core edit, no new architecture:

1. **Grain**: either (a) operational — every future `gena_tfp_bundle_run.py`/
   `run_tfp_file_pipeline.py` invocation for TFP work must export `HESPERIA_AREA_MATH_GRAIN=10`
   (zero code change, but relies on every caller remembering it — the same class of gotcha as the
   `/data/workspaces/hesperia` stale-checkout issue already documented twice in the deployment
   map), or (b) code fix — have `run_tfp_file_pipeline.py` call
   `apply_analyze_profile_defaults(profile="tfp")` itself (or at minimum
   `os.environ.setdefault("HESPERIA_AREA_MATH_GRAIN", "10")`) near its own TFP-profile env setup,
   matching what the live service already does automatically. **(b) is the more robust fix** —
   removes a footgun instead of documenting it.
2. **marker_index**: pass `marker_index=build_marker_to_concepts()` (or reuse
   `session_parser.py::_get_merged_marker_index()` for the colloquial-enhanced variant, matching
   what `analyze_session_enhanced`/`analyze_session_speaker_aware` already do) at the
   `run_session_kme_pipeline()` call site in `run_tfp_file_pipeline.py`, or push the default one
   level in and give `run_session_kme_pipeline()` itself the same
   `marker_index if marker_index is not None else build_marker_to_concepts()` pattern the other two
   parameters already have, closing the gap for every future caller, not just this one call site.

## 4. Config

No new env vars for the marker_index fix. Grain fix option (a) needs
`HESPERIA_AREA_MATH_GRAIN=10` set at every TFP batch invocation; option (b) needs no caller action.

## 5. Invocation

N/A — spec only, nothing to invoke yet.

## 6. Expected output shape (once fixed)

`07_session_kme.json` → `report.primitives.area_math_grain` / `report.derived.area_math_grain`
read `10`, not `12`; `KDI`/`CCI`/`COH` etc. become validly comparable against the TFP-specific
family-grain grounding checks and corpus `S`/`T` scores already computed in the same bundle run.
Single-token marker coverage adds incremental concept hits on top of the existing phrase-based
signal — expect a modest, not dramatic, shift in `CI`/`NC`/derived metrics per session (phrase
detection was already the priority channel and already worked).

## 7. Validation evidence

None yet — this is the pre-implementation spec. Validation plan once built: rerun the same 14
real sessions already on disk (`outputs/tfp/runs/tfp_gena_*_corpuscalib/`), diff `area_math_grain`
(expect 10) and the primitive/derived values before/after, confirm no exceptions, full calibration
pytest suite green, same rigor as every other change this session.

## 8. Rollback

Grain fix (b): revert the `setdefault`/profile-defaults call. Marker-index fix: drop the
`marker_index=` kwarg back to unset — falls back to today's (degraded but non-crashing) behavior.
Neither touches sealed code or existing calibration YAMLs.

## 9. Scope note

Both fixes are pipeline **call-site wiring** (which existing, already-correct functions get
called with which existing, already-built ontology data) — not new math, not a sealed-layer edit,
not a documented-parameter toggle either. Per `SPEC-ETHAN-CHIRON-HESPERIA-CALIBRATION-ENTITY.md`
§5 ("may propose, not implement alone: any change to the sealed pipeline's behavior that isn't a
documented-parameter toggle... new layer logic"), routing this through `inbox.md` → triage before
either fix lands, rather than merging directly.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-20 | investigation + fix proposal, not yet implemented
