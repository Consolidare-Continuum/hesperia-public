# Layer 10 — Analysis Report / Interpretation (declared, not yet implemented)

## Status: placeholder layer with an active contract

L10 has no `core/layers/layer_10.py`. The only existing implementation is a
three-line stub inside `sphere/pipeline/pipeline_runner.py`:

```python
layer_outputs["layer_10"] = {
    "analysis_report": None,
    "interpretation":  None,
    "explanation":     None,
    "_placeholder":    allow_l10_placeholder,   # config key "allow_placeholder_layer10", default True
}
```

The placeholder is injected unconditionally on every pipeline run, after L9
produces rule triggers and before contract validation. It satisfies the
contract because `contract_validation.py` lists `_placeholder` in the same
key-group as `analysis_report`, `interpretation`, and `explanation` — any one
of those four keys present is sufficient to pass the output contract check
for `layer_10`.

## What L10's contract specifies (the intended layer)

The contract definition (`sphere/pipeline/contract_validation.py`) records a
single field group for L10:

```python
"layer_10": [
    ["analysis_report", "interpretation", "explanation", "_placeholder"],
],
```

The field names declare the intent: L10 is designed to be the
**synthesis-to-output boundary** — the layer that converts the accumulated
structural measurements, rule trigger outputs, and semantic state of L1–L9
into a structured interpretive account. `analysis_report` would carry the
aggregate analysis; `interpretation` would carry a structured semantic
characterisation; `explanation` would carry the auditable reasoning chain.
All three are `None` in the current placeholder, meaning no conversion
happens. The raw L1–L9 outputs and the USF assembly that follows pipeline_runner
directly are what downstream consumers receive instead.

The debug interface (`sphere/interfaces/debug_interface.py`) already includes
L10 in its layer enumeration ("layer_1 .. layer_10"), which means it is
visible to any tooling that introspects the full layer output dict — it just
carries null payloads.

## The one live consequence: Theta THETA_004

L10's placeholder status has an active effect on the governance guard. Theta
(`sphere/guards/theta_governance.py`) collects a fact `layer10_placeholder`
from the artifact dict:

```python
l10 = art["layer_outputs"].get("layer_10", {})
facts["layer10_placeholder"] = l10.get("_placeholder") is True
```

Rule THETA_004 fires on that fact:

```
rule_id:   THETA_004
severity:  medium
condition: layer10_placeholder == True
action:    flag_non_canonical_interpretation
message:   "Placeholder Layer-10 cannot upgrade output to canonical narrative truth."
```

THETA_004 does not block a run — `flag_non_canonical_interpretation` is not
a hard rejection action — but it marks the pipeline output as non-canonical.
Any output produced while L10 is a placeholder carries this governance flag:
the system explicitly acknowledges that it has not performed the
interpretation synthesis step, and downstream consumers reading
`theta_result.governance_flags` will see it. This is the same pattern used
elsewhere in the guard triad: a missing or incomplete layer does not silently
pass; it degrades the output's certification level rather than producing an
error.

The logic bridge (`sphere/fpf_bridge/logic_bridge.py`) also references L10 in
its docstring ("Build fpf LogicLayer from sphere L9/L9b/L10 outputs") —
confirming that when L10 is eventually implemented, its output is intended to
flow into the fpf-thinking-map's `LogicLayer`, alongside L9's rule triggers
and Prolog-derived facts, as the third input to that synthesis bridge.

## Relationship to the existing L1–L9 layers

Every layer from L1 through L9 produces a measurement: activation census,
topology traversal, shadow comparison, evidence retrieval, counter-evidence,
dynamism metrics, consistency classification, unit standardisation, rule
triggers. L10's declared role is to take those measurements collectively and
produce a **synthesis artifact** — not another measurement, but an account
of what the measurements mean together. The distinction between L1–L9
(measurement) and L10 (synthesis) mirrors the classical analysis-vs-interpretation
boundary in signal processing: L1–L9 are the forward transform (raw text →
structural features); L10 is the inverse step (structural features → structured
semantic description), the step that must hold the entire feature vector in
scope simultaneously.

Because that step requires access to all prior outputs at once, it is
structurally impossible to implement without the full pipeline context —
which is why `pipeline_runner.py` is the right home for it and why no
standalone `layer_10.py` can implement it in isolation. When implemented,
L10 will read directly from the `layer_outputs` dict that accumulates across
L1–L9, produce `analysis_report`, `interpretation`, and `explanation` payloads,
and hand them to both the fpf bridge's `LogicLayer` constructor and to the USF
assembly that pipeline_runner performs after L10 returns.

## Relationship to neighboring layers and corners

- **L9** (`layers/L9_pillars_and_brand_labels.md`) — the last implemented
  layer; its `triggered_rules` and `structural_diagnostics` are the
  immediate input L10 is designed to consume.
- **`corners/fpf_bridge.md`** — the fpf `LogicLayer` constructor explicitly
  names L9/L9b/L10 outputs as its three inputs; L10 is the missing third.
- **`corners/guards.md` (Theta THETA_004)** — the active governance
  consequence of L10's placeholder state; any current run carries this flag.
- **`corners/sphere_pipeline.md`** — the L1–L10 orchestrator; L10's slot
  in the pipeline contract is reserved and validated on every run even while
  the implementation is absent.
