# HSR-V7 Core Output Wiring Convergence Report

## Outcome

Core output wiring was converged around the existing canonical `core.domain` output contract.

No new feature layer was added.
No calibration or version authority was changed.
No files were deleted.

## Change Made

The compatibility bridge `hesperia.engine.kme.clinical_bridge.run_kme_from_activation` now populates `MetricReport.primitive_map` and `MetricReport.derived_map` from the already-built fingerprint maps instead of recomputing local report maps from `primitives.to_dict()` and `derived.to_dict()`.

## Why This Matters

Before this pass:

- canonical core pipeline path used fingerprint-owned maps
- compatibility bridge path used locally recomputed maps

Even when values matched today, the authority was split. That created avoidable drift risk in:

- runtime JSON serialization
- future rounding or ordering changes
- report-vs-fingerprint consistency assertions

After this pass:

- both document-output paths use fingerprint-owned maps as the source of truth

## Output Contract Status

- `primitives`: CANONICAL-WIRED
- `derived`: CANONICAL-WIRED
- `fingerprint`: CANONICAL-WIRED
- `triz`: CANONICAL-WIRED
- `profile`: CANONICAL-WIRED at corpus level
- `classification`: IMPLEMENTED-NOT-DOCUMENTED
- `topology`: IMPLEMENTED-NOT-DOCUMENTED as intermediate wiring
- `provenance`: DOCUMENTED-NOT-IMPLEMENTED as dedicated report field
- `calibration_pack`: DOCUMENTED-NOT-IMPLEMENTED as dedicated report field

## Tests Added

`tests/test_core_output_wiring.py` now verifies:

- canonical core report maps equal fingerprint maps
- compatibility bridge report maps equal fingerprint maps
- canonical JSON keys remain `sourceId`, `primitives`, `derived`, `fingerprint`, `triz`
- version and hash metadata survive serialization

## Source-Truth Documents Added

- `docs/specs/HSR-V7-CORE-OUTPUT-CONTRACT.md`
- `docs/archive/HSR-V7-CORE-OUTPUT-WIRING-INVENTORY.md`
- `docs/archive/HSR-V7-CORE-OUTPUT-WIRING-CONVERGENCE-REPORT.md`

## Residual Notes

- Current document-level KME report JSON does not expose a standalone top-level `provenance`, `calibration_pack`, or `topology` field.
- That absence is now explicit documentation, not hidden ambiguity.
