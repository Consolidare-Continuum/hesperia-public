# Corner: Layer Contracts and Attribution (`core/contracts/`, `core/attribution/`, `core/result/`)

## Why this corner exists at all

A nine-to-eleven-layer pipeline (L1 through L9, plus interpretation/USF and
the fpf_bridge) is only as trustworthy as the discipline enforced *between*
layers. Without an explicit contract, each layer's author could pass
ad hoc dicts with whatever shape was convenient that day, and a Gamma-style
"layer_order_valid" check would have nothing fixed to validate against.
`core/contracts/layer_contract.py` exists to make every layer's
input/output shape an explicit, shared type
(`LayerInput(text, tokens, metadata)` → `LayerOutput`), so that "did this
layer receive what it expected" is a structural question, not a documentation
convention people might forget to follow.

## Why this had to be minimal (a single `run()` entry point, not a rich plugin interface)

The contract docstring states the rule directly: "Single public entry point
per layer: run(input_data) -> LayerOutput." A richer interface (multiple
methods, optional callbacks, layer-specific kwargs) would have let
individual layers grow inconsistent surface area over time, exactly the kind
of inconsistency Gamma's `layer_order_valid` and `no_illegal_mutation_of_upstream`
invariants exist to catch. Keeping the contract to one method forces every
layer's complexity to live *inside* the layer, where it's locally testable,
rather than leaking into the orchestration boundary where it would be far
harder to audit.

## Why attribution (`core/attribution/`) is a distinct concern from the resolver

The resolver (`corners/lexicon_resolver.md`) decides which concept a span
resolves to. Attribution is the *aggregate* of those decisions back up to the
family level for a whole text (`dict_a_v06.jsonl` token→288-family weights,
sentence = mean, dominant = argmax). These are different operations at
different scales — span-level disambiguation vs. whole-text aggregation — and
treating them as one module would conflate "did we resolve this word
correctly" with "what does the resolved evidence add up to for this text,"
which need different test strategies (the first is tested per-span against
fixtures; the second is tested against whole-text calibration corpora). The
attribution module's explicit dependence on a frozen lexicon bundle
(`assets/lexicon/frozen/v0_5_0`) is what lets attribution be re-run and get bit-identical
results without re-deriving resolver logic each time.

## Why result contracts (`core/result/contract.py`, `compare.py`) exist separately from the pipeline itself

Once Hesperia has more than one consumer of a pipeline result (CLI, API,
internal services, eventually fpf_bridge), there has to be one place that
defines "what counts as a comparable result" — otherwise every consumer would
re-implement its own notion of result equality/diffing, and a regression test
comparing two runs would be only as good as whichever ad hoc comparison logic
happened to be used. `core/result/compare.py` exists to make result
comparison itself a single, reusable, tested operation rather than scattered
logic duplicated wherever two outputs need to be diffed (USF fingerprint
diffing in `sphere/usf/fingerprint_diff.py` is a layer-specific analogue of
the same need).

## Relationship to neighboring corners

- The contract layer is what makes the layer-by-layer narrative used
  throughout this documentation package (`L1 → L2 → ... → L9 → USF`) a real,
  enforced structure rather than a description of convention.
- Attribution is the bridge between `corners/lexicon_resolver.md` (per-span
  resolution) and `corners/hex_substrate.md`/`corners/propagation_dynamics.md`
  (whole-field aggregation).
