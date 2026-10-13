# Corner: Release Governance — Sealing as a Claim About *Which Exact Tree* Shipped

**Location:** `release_sealed_runtime.sh`, `make_release.sh`, `build_shipping.sh`,
`Dockerfile.shipping`, `Dockerfile.product`, `release/` (per-version release notes and scopes),
`docs/DEV-READY-LINE-2026-05-18.md`, `EXTENSION_STATUS.yaml`, `VERSION.yaml`'s `build:` block.

**Born:** first sealed-runtime gate and architecture-fingerprint provenance chain at the v0.4.1 era
(`c1361131 docs: add Git tag and SHA to ARCHITECTURE_FINGERPRINT proof`, `e23749e3 docs: evidence
chain in ARCHITECTURE_FINGERPRINT (document→commit→tag)`, `b1e0feac docs: OpenTimestamps proof`);
matured into the full dev/prod split at the 0.6.x era (see `corners/release_seal.md`,
`eras/05_sealed_0.6.x.md`).

## Why this is a distinct concern

"Deterministic" and "sealed" are different claims. Determinism is a property of the *code* (same
input, same output). Sealing is a claim about *which exact tree* — code, lexicon, calibration
profile, dictionary version — was the one validated, frozen, and shipped. Without an explicit
sealing mechanism, "the system is deterministic" says nothing about whether the artifact a consumer
is running today is the artifact that was actually tested.

`VERSION.yaml`'s structure makes the point: `system_version`, `components.*`,
`calibration.active_profile`, `defaults.active_calibration_dict_pack`, and `build.git_commit`
(filled at runtime, "never commit secrets here") all have to agree for a release to be meaningfully
"the same system" twice. `tfp_module_v1.pinned_calibration_dict_pack` must match
`defaults.active_calibration_dict_pack` "for mainline" — an explicit cross-check the release
process enforces, the same pattern as the `anchor_map_v1` FROZEN-status check in the metric
registry (`corners/metric_registry.md`).

The dev/prod split is this corner's most structurally significant decision: a single sealed-runtime
gate cannot reason meaningfully about a tree that mixes production code with pitch decks, research
scratch corpora, and dev-only governance prose, because changing a slide would invalidate the seal
hash for no architecturally relevant reason. `EXTENSION_STATUS.yaml`'s `product_surface` field
(`none` / `internal` / `optional`) is the same discipline at a finer grain — marking which
extensions (`dynamics`, `triz`, `clinical_tfp`) are even eligible to appear in a public surface,
independent of whether they are technically implemented.

## What would break without it

Without sealing, a downstream consumer (or future self) auditing a verdict produced months ago
would have no way to reconstruct which lexicon version, which calibration profile, and which code
commit produced it — defeating the purpose of building a deterministic pipeline in the first place,
since determinism is only useful if you can also prove *which* deterministic run you are looking
at. Without the dev/prod split, every cosmetic dev-only change would force a re-seal of the
production artifact, eventually causing teams to stop trusting the seal at all — the same
"if everything requires re-validation, nothing gets validated carefully" failure mode the lexicon
and calibration corners' narrower freeze boundaries also exist to prevent.

## How it relates to neighbors

Release governance is the outermost wrapper around every other corner — it is what asserts, after
the fact, that Sigma/Gamma/Theta passed (`corners/guards.md`), that the lexicon and calibration pins
matched (`corners/lexicon_resolver.md`, `corners/calibration.md`), and that the resulting artifact
corresponds to a specific commit. `release/v0.7.0/RELEASE_SCOPE.md` shows this corner actively
scoping the metric-registry era's rollout ("Include: anchor_map_v1 (FROZEN option A),
hesperia_metric_emit.py with HESPERIA_METRIC_EMIT=1... Deferred: HESPERIA_GCS_EMIT, full IPoW emit,
path_metric_cost on traversal") — meaning release governance is also the mechanism by which
"minimal right move" architectural restraint gets formally recorded and enforced, not just argued
for in a spec document.
