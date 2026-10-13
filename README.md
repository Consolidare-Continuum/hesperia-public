# Hesperia 1.0.0

**Copyright © 2026 CONSOLIDARE CONTINUUM S.R.L.** (IDNO 1026023120076). All rights reserved.
Licensed under **CC-HES-LIC-1.0**. See [LICENSE](LICENSE), [docs/iso/CC-HES-LIC-1.0.md](docs/iso/CC-HES-LIC-1.0.md), [NOTICE](NOTICE), [LEGAL_NOTICE.md](LEGAL_NOTICE.md).
Source-visible, **not** open source and **not** MIT.

Hesperia is a **pre-LLM / post-RAG** structural reasoning engine. It compiles input into a governed topology
(12 areas × 24 families = 288-cell canon matrix) *before* any language model is called
([sphere/router/pre_llm_compiler.py](sphere/router/pre_llm_compiler.py)). It does not retrieve and paraphrase:
evidence comes from deterministic calibrated dictionaries, and the LLM, where one is used, sits downstream of the structure.

- **FPF thinking map**: native bridge to [`fpf-thinking-map`](https://github.com/Consolidare-Continuum/fpf-agentic-thinking-map)
  ([sphere/fpf_bridge/](sphere/fpf_bridge/), [sphere/fpf_inspect/](sphere/fpf_inspect/); pin in [requirements/router.txt](requirements/router.txt)).
- **Default modules**: [hesperia/modules/default/](hesperia/modules/default/) (dict A/B, metrics, topology), HSPR default SKU,
  and [hesperia/modules/tfp/](hesperia/modules/tfp/) (TFP Class B, forever free).
- **Release seal**: [release/v1.0.0/SEAL.md](release/v1.0.0/SEAL.md). ISO-style documentation: [docs/iso/](docs/iso/).

## What this public tree does not contain

See [PUBLIC-RELEASE.md](PUBLIC-RELEASE.md). In short, the syzif reference library (third-party copyrighted books) is withheld,
and its **bibliography is public**: [hesperia/modules/default/corpus/SYZIF-BIBLIOGRAPHY.md](hesperia/modules/default/corpus/SYZIF-BIBLIOGRAPHY.md).
Clinical session material and book full-text corpora are also withheld. Tests that depend on withheld data will skip or fail in this tree.

## Architecture


Current architecture authority:

- `core.domain` is the canonical shared KME/domain computation layer.
- `core.runtime` is the canonical generic runtime module layer.
- `hesperia.engine.kme` remains a narrowed compatibility package surface, with protected legacy bridge behavior.
- former `hesperia.modules.core` / `metrics.base` / `topology.core` shim files were removed after convergence to `core.runtime.*`.
- `hesperia.modules.tfp` remains the domain extension.
- `core.topology.invariant_catalog` is the single canonical source for the canon matrix (12 areas × 24 families = 288) — see [docs/TOPOLOGY_INVARIANTS.md](docs/TOPOLOGY_INVARIANTS.md).
- `core.attribution` has two live modules (`attribution_shared.py`, sole path via `runtime/pipeline/analyze.py`; `structural.py`, r1_r4-only) — see [docs/foundations/attribution_layer.md](docs/foundations/attribution_layer.md). The former "v06" module (`attribution.py`, a synthetic-placeholder dictionary — no real vocabulary) was retired 2026-07-30. Core has no relation to any extension/module (TRIZ, TFP, clinical, or otherwise).
- Canon matrix family names sourced from the sphereV genesis book corpus (adopted 2026-07-30) — see [docs/foundations/genesis_taxonomy_provenance.md](docs/foundations/genesis_taxonomy_provenance.md).
- Any loop calling a paid/rate-limited external API (OpenAI today) must durably persist each call's result before the next call starts — a crash between calls must never cost more than the one in-progress call. Binding rule, enforced at the shared `chat_json()` entrypoint — see [docs/conventions/API-CALL-DURABILITY.md](docs/conventions/API-CALL-DURABILITY.md).

| Line | Tag |
|------|-----|
| Rollback (2026-05-18) | `hesperia/rollback-line-20260518` |
| Dev-ready (this) | `hesperia/dev-ready-line-20260518` |
