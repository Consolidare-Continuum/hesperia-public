# sphere/diagnostics — DEPRECATED (CHI-B16-03 / CHI-006)

This package is **not** on any live product path. It has zero callers and zero
tests. Keep the code for historical reference; do not tune
`assets/specs/canon/diagnostic_rules.yaml` as a Tier-B calibratable pack.

**Canonical live diagnostics:** `assets/specs/canon/logic_rules.yaml` +
`sphere/logic/rule_engine.py` (Layer-9), used via `sphere/pipeline/pipeline_runner.py`
on `/product/tfp`, `/product/fingerprint`, `/product/llm-audit`.

**Do not** wire `run_diagnostics()` into `product_interpret_service.py` without a
new Grace-triaged product decision.
