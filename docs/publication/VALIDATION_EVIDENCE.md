# Validation evidence index

This document is an index of what is actually provable today, cited exactly — no new claims. Every
number below was directly re-run and verified during this documentation program (commit `63a2295b`,
`main`), not copied from an earlier report without re-checking. Where a figure differs from a
previously-circulated number, the previously-circulated number is not corrected here — only the
freshly-verified figure is asserted, with its exact scope stated.

## 1. Router / calibration / product-interpret test suite

Command run: `pytest tests/router tests/calibration tests/test_product_interpret_api.py`

| Metric | Verified value |
|---|---|
| Collected tests | **76** (`tests/calibration/test_llm_calibration.py`: 7; `tests/router/test_llm_call_boundary.py`: 6; `tests/router/test_post_llm_audit.py`: 5; `tests/router/test_pre_llm_compiler.py`: 3; `tests/router/test_prompt_envelope.py`: 7; `tests/router/test_router_fingerprint_v0_1.py`: 5; `tests/router/test_router_gold_fixtures.py`: 2; `tests/router/test_router_gold_matrix.py`: 11; `tests/router/test_router_governance_modes.py`: 16; `tests/router/test_router_json_schema.py`: 6; `tests/router/test_tool_inquiry_gate.py`: 4; `tests/test_product_interpret_api.py`: 4) |
| Run result | Exit code `0`, no failures shown in dot output, full run completed |

**Scope note:** this is narrower than the full repository test surface (294 test files total under
`tests/`, per `docs/iso/QUALITY_MODEL.md`). This figure covers specifically the V7 router,
calibration, and `/product/interpret` surfaces — the governed LLM-boundary path described in
`docs/publication/METHODS.md` §5. In the repo's later productization language, this is also the
strongest currently-cited validation surface behind phrases like **deterministic validation** and
**audit trace**. It does not represent a full-repository pass rate claim, and it does not by
itself validate pricing, willingness-to-pay, or other GTM claims preserved separately in
`UPCELERATOR_PRODUCTIZATION_QA.md`.

## 2. Source-of-truth verification script

`tools/verify-hesperia-v7-source-truth.sh` (HSR-V7-A-11) checks, on a dev clone: that
`sphere/router/thinking_map_bridge.py` exists, that the `fpf-thinking-map` package pin is
documented, and that router tests pass. This is the mechanized version of the same claim §1 verifies
manually — cited here as the repeatable check, not re-run in this pass since §1 already covers its
test-pass component directly.

## 3. Release-scope evidence (what shipped, what was deferred)

`release/v0.7.0/RELEASE_SCOPE.md` (already cited in `docs/iso/LIFECYCLE_PROCESS.md` §4) is itself a
form of validation evidence: it states exactly what was included in that release
(`anchor_map_v1` FROZEN, `hesperia_metric_emit.py`) and what was explicitly deferred
(`HESPERIA_GCS_EMIT`, full IPoW emit, `path_metric_cost`) — a released-scope claim that can be
checked against the actual shipped files, not an aspirational roadmap.

## 4. Determinism evidence

`core/guards/determinism.py` and the release bundle's `determinism_report.json`
(`docs/iso/LIFECYCLE_PROCESS.md` §4) are the mechanism by which "same input, same output" is
actively tested per build, not assumed from architecture. This document does not re-run a
determinism check in this pass — the mechanism's existence and its role in the seal process is
already verified in `corners/release_seal.md`. This is the technical substrate underneath the
productization phrase **stable, auditable meaning by design**: the wording is marketing-facing, but
the determinism claim it points to is meant literally and is backed here by named mechanisms.

## 5. What this index does not yet cover

- **The full L1–L9 deterministic pipeline's own test suite** (as distinct from the router/LLM
  boundary tests in §1) is not separately re-run and counted in this pass. A follow-up validation
  pass should add a row here with the same exact-count discipline used in §1.
- **Calibration validation against the "20–50 TFP transcripts"** `specs/canon/activation_calibration.yaml`'s
  own comment calls for (`corners/calibration.md`) is a real, cited requirement, not a completed and
  measured validation result in this document — do not cite this section as evidence that
  calibration validation has been performed at that scale.
- **`hesperia/extensions/dynamics/`** has its own test files (`tests/test_field_dynamics_calibration.py`
  and neighbors) but, per `docs/publication/NOVELTY_AND_POSITIONING.md`'s "do not overclaim"
  section, passing tests for a subsystem with no product-surface wiring is not validation evidence
  for a product claim — it is evidence only that the subsystem's own internal logic is
  self-consistent.

## Maintenance note

Registered in `docs/iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`. Re-run §1's command and update the
collected-test count whenever a new test file is added to `tests/router`, `tests/calibration`, or
`tests/test_product_interpret_api.py` — a stale count here is worse than no count, since it implies
a false precision.

## Navigation

← [`../README.md`](../README.md) (start here) · [`../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md`](../iso/DOCUMENTATION_TRACEABILITY_MATRIX.md) (master registry)
Related: [`METHODS.md`](METHODS.md) (what this evidence validates) · [`REPRODUCIBILITY_PACKAGE.md`](REPRODUCIBILITY_PACKAGE.md) (pins/seeds needed to re-run these tests identically) · [`../iso/QUALITY_MODEL.md`](../iso/QUALITY_MODEL.md) (the 294-test-file figure this document's 76-test scope is a subset of)
