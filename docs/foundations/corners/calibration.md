# Corner: Calibration (`hesperia/engine/calibration*`, `assets/calibration/`, `openai_calibrate_*.py`, `assets/lexicon/frozen/v06/calibration_stats_v06.json`)

## Why this corner exists at all

Every threshold elsewhere in the system (activation thresholds, entropy
bounds, monotony cutoffs in `diagnostic_rules.yaml`) is a number that someone
had to choose, and a chosen-once number is a liability unless there is a
controlled, repeatable process for re-deriving and re-validating it against
real text. Calibration exists to make threshold-setting itself a governed,
versioned, falsifiable process rather than a one-off tuning pass that nobody
can reproduce later. `specs/canon/activation_calibration.yaml`'s own comment
— "Tune after validation on 20–50 TFP transcripts" — states the discipline
directly: a threshold is not canon until it has been validated against a
labeled corpus, and the validation process has to be repeatable so a future
threshold change can be judged against the same bar.

## Why calibration is split into profiles (`calibration_profile.py`,
`assets/calibration/profiles_v1.json`) rather than hardcoded constants

A single global threshold set can't serve every consumer: a research/
exploratory run, an internal review, and a ship-blocking release gate
legitimately need different tolerance for noise. `calibration_release_gate.py`'s
profile aliasing (`research_allow_degraded` → `exploratory_allow_degraded`,
`product_candidate` → `engine_release_candidate`, etc.) shows this was
recognized explicitly: rather than have several hardcoded threshold sets
scattered through code, the system names the *intent* of a run (how much risk
is acceptable) and resolves that intent to one canonical, versioned profile
document. This keeps "what does this profile actually permit" a single
auditable JSON file rather than a set of conditionals duplicated across call
sites.

## Why the LLM-driven calibration scripts (`openai_calibrate_areas.py`,
`openai_calibrate_dict_a.py`, `openai_calibrate_topology.py`) are offline tools, not runtime dependencies

Using an LLM to help build or audit calibration data (propose candidate
dictionary entries, audit area assignments) is acceptable specifically
*because* it happens offline, against a fixed corpus, with output reviewed and
frozen before it ever reaches the deterministic runtime. The moment an LLM
call became part of the live `/analyze` path's calibration logic, the
determinism guarantee that the rest of the system is built around would be
gone. Keeping these scripts as one-time, audited, offline batch tools — whose
output becomes a frozen, checksummed dictionary or weight file — lets the
system benefit from LLM-assisted authoring without paying the determinism
cost at inference time. This is the same boundary the design memo draws
explicitly when distinguishing "LLM produces language" from "Hesperia
produces authority": calibration tooling is allowed to use an LLM because its
output becomes canon *data*, never canon *logic*.

## Why calibration artifacts are pinned by name in `VERSION.yaml`
(`active_calibration_dict_pack: "archive_063_minimal"` as of commit `63a2295b` — this pin moves
with the release; re-read `VERSION.yaml` directly rather than trusting this example value, per
`docs/publication/REPRODUCIBILITY_PACKAGE.md` §1)

Pinning the exact dictionary-pack name in the single system-version source of
truth — rather than letting the runtime pick "whatever calibration data is
present" — is what makes `validate_version_consistency` (referenced in
`release/v0.6.0/RELEASE_SCOPE.md`) meaningful: a release can be checked
mechanically for whether its calibration data actually matches what the
version claims to be running. Without this pin, two builds claiming to be
"v0.6.0" could silently use different calibration data and produce different
results for the same input — exactly the kind of drift the seal process
exists to prevent (see `corners/release_seal.md`).

## Relationship to neighboring corners

- Calibration output (thresholds, profile bundles, frozen dictionary packs)
  is consumed by `corners/lexicon_resolver.md` (Dict A/B), `corners/logic_guards.md`
  (rule thresholds), and `corners/shadow_correction.md` (entropy/dominance
  parameters).
- Is the corner the TFP-specific gates (`TFP-GATE-A0`, `TFP-TIGHT-*`,
  `TFP-REL-*` — visible in the v0.5.x commit history) were built to enforce:
  calibration must be validated, gated, and only then pinned, never silently
  swapped.
- Feeds the release/seal process described in `corners/release_seal.md`,
  which checks calibration pin consistency as part of certifying a build.
- Distinct from `corners/field_dynamics.md`'s own `calibration.py` (HSPR Calibration Index, a
  grid-search fitness function scoped only to tuning the Phase-N theta constants) — that is a
  narrower, self-contained instance of "calibration as a governed process," not yet integrated
  into the pinned `active_calibration_dict_pack` this corner describes.
