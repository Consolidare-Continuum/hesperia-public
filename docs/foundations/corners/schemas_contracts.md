# Corner: Schemas and Contracts — USF and the Frozen `/analyze` HTTP Contract

**Location:** `schemas/` (anchor_map_v1.json, hesperia_metric_v01.json, plus PCH/production
schemas), `core/contracts/layer_contract.py`, `specs/canon/usf_schema.json`,
`docs/ENGINE-ANALYZE-CONTRACT.md`.

**Born:** the USF (Universal Structural Fingerprint) schema solidifies at `63febce1 Layer-10
interpretation, USF consolidation`; the `/analyze` HTTP contract is explicitly frozen later at
HSPR-01/02 (2026-06-11): "Frozen — Python side (`HesperiaPublicSnapshot`, `HesperiaEngineBridge`)
parses against this contract."

## Why this is a distinct concern

A pipeline can be internally deterministic and still fail every external consumer if its output
shape is allowed to drift silently. This corner exists to make "the shape of what comes out" itself
a versioned, checkable artifact — separate from the correctness of the values inside that shape
(which Sigma/Gamma/Theta already check internally; see `corners/guards.md`).
`docs/ENGINE-ANALYZE-CONTRACT.md` states the boundary enforcement directly: "the engine must return
all fields listed below. Python side raises `ValueError` if any mandatory field is absent" — the
contract is enforced at the boundary, not just documented.

`core/contracts/layer_contract.py`'s `LayerInput` type is the inter-layer analogue at a finer
grain: where the `/analyze` contract governs the external HTTP boundary, `LayerInput` governs the
boundary between any two adjacent layers inside L1–L10, checked by
`sphere/pipeline/contract_validation.py` (see `corners/sphere_pipeline.md`,
`corners/layer_contracts_attribution.md`).

## What would break without it

Without a frozen `/analyze` contract, the Python-side public-snapshot/bridge classes
(`HesperiaPublicSnapshot`, `HesperiaEngineBridge`) would have to defensively guess at field
presence on every call, and any internal refactor of pipeline output shape would silently break
external callers with no compile-time or test-time signal. Without the USF as a single
consolidated fingerprint, Theta's "required artifacts present" check (USF, raw_metrics,
logic_outputs, provenance — see `corners/guards.md`) would have nothing single to check; it would
have to enumerate every individual sub-output dict by hand, a check that would itself drift out of
sync as new layers were added.

## How it relates to neighbors

The USF is what Theta's governance rules gate on, and what the fpf_bridge's input contract is
literally built from (`specs/canon/fpf_bridge_v7.md`'s "Input Contract" mirrors the USF-derived
result dict almost verbatim: `shadow_metrics`, `logic_metrics`, `interpretation_metrics`,
`prolog_logic`, `guards`, `dynamism_metrics` — see `corners/fpf_bridge.md`,
`corners/interpretation_usf.md`). The new `schemas/hesperia_metric_v01.json` (v0.7.0, uncommitted)
is this corner's pattern extended to the metric-registry's optional `meta.hesperia_metric` block —
a new schema file precisely because the metric registry's emit format needed its own frozen,
versioned contract rather than being bolted onto the existing USF schema, keeping the metric
emit's optionality (gated behind `HESPERIA_METRIC_EMIT`) cleanly separable from mandatory USF
fields (see `corners/metric_registry.md`).
