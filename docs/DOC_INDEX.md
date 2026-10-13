# Hesperia documentation index

**Updated:** 2026-08-17 (dev/train boundary)

## Agentic entry

| Doc | Topic |
|-----|--------|
| [foundations/agentic_orientation.md](foundations/agentic_orientation.md) | Five-pass cold-start protocol for agentic work: branch naming, math posture, owner map, anti-drift rules |
| [../AGENTS.md](../AGENTS.md) | Repo-local execution rules and Hesperia-specific behavior — includes the dev/train mode-marker rule |
| [recipes/README.md](recipes/README.md) | Task → Hesperia-capability recipes (Chiron's required output); shape + when a theorizing note replaces a recipe |
| [recipes/params_combo/INDEX.md](recipes/params_combo/INDEX.md) | Addressable registry of multi-parameter combo recipes (`PC-NNN` IDs) — one place for recipes that tune more than one parameter at once |
| [recipes/chiron_tweaks/INDEX.md](recipes/chiron_tweaks/INDEX.md) | Addressable registry of genuinely-usable new-capability tweaks (`CHI-NNN` IDs) — as opposed to tuning existing parameters |

## Layer 11 — fpf_bridge (LLM reasoning bridge) and its extensions

| Doc | Topic |
|-----|--------|
| [foundations/corners/fpf_bridge.md](foundations/corners/fpf_bridge.md) | Why the bridge exists, the read-only-against-sphere guarantee, what's borrowed from FPF vs. Hesperia-native |
| [../specs/canon/fpf_bridge_v7.md](../specs/canon/fpf_bridge_v7.md) | Original v7 bridge spec |
| [../specs/canon/fpf_bridge_v7_2_evidence_expansion.md](../specs/canon/fpf_bridge_v7_2_evidence_expansion.md) | Full parameter inventory (~239 L1–L9 vars + 41 KME + 3 TRIZ), COBALT+TFP scope, Phase 1–4 code shipped |
| [../specs/canon/fpf_bridge_v7_3_agentic_cursor_interface.md](../specs/canon/fpf_bridge_v7_3_agentic_cursor_interface.md) | `runtime/agentic_bridge/` — read-only + validation tools for an external agent (Cursor) |
| [../specs/canon/fpf_bridge_v7_4_cobalt_corpus_scaleup.md](../specs/canon/fpf_bridge_v7_4_cobalt_corpus_scaleup.md) | COBALT's pilot-vs-production corpus attribution gap, named explicitly |
| [foundations/provenance.md](foundations/provenance.md) | Which FPF sections are actually verified-wired vs. spec-only claims |

All three v7.2–v7.4 specs are **ratification-pending** (Ethan) as of this update — status line at
the top of each spec is authoritative, not this index.

## Parameter wiki (Colombo mirror)

| Doc | Topic |
|-----|--------|
| [brain-export/colombo/hesperia-wiki/](brain-export/colombo/hesperia-wiki/) | LIVE/DEAD math variables register — mirror of brain `colombo_research/hesperia/wiki/`; LAN serve stays on altitudine |

## Geometry and metric

| Doc | Topic |
|-----|--------|
| [foundations/parameter_rationale_and_theory.md](foundations/parameter_rationale_and_theory.md) | Why the constants have these values/ranges, and what theory families they belong to |
| [24_SPEC__Hesperia_Metric_and_Distance_v0_1.md](specs/24_SPEC__Hesperia_Metric_and_Distance_v0_1.md) | **HesperiaMetric** registry, `metric_layer` enum, `S_path`, runtime emit flags |
| [ENGINE-ANALYZE-CONTRACT.md](../ENGINE-ANALYZE-CONTRACT.md) | `/analyze` response — optional `meta.hesperia_metric` when `HESPERIA_METRIC_EMIT=1` |

## Canon matrix and attribution

| Doc | Topic |
|-----|--------|
| [TOPOLOGY_INVARIANTS.md](TOPOLOGY_INVARIANTS.md) | The canon matrix (12 areas × 24 families = 288): canonical source, full named taxonomy (sphereV genesis, adopted 2026-07-30), geometry constants, do-not-duplicate rule |
| [foundations/genesis_taxonomy_provenance.md](foundations/genesis_taxonomy_provenance.md) | Where the family names came from (sphereV genesis book corpus), what was/wasn't changed, what Stage 2 (real dictionaries) still needs |
| [foundations/attribution_layer.md](foundations/attribution_layer.md) | Which `core.attribution` module is live (attribution_shared.py, sole path) vs. retired (attribution.py/"v06" — synthetic placeholder dictionary) vs. r1_r4-only, and core's severance from every extension/module |

## Cross-links (brain authority)

- **20_GEOMETRY** — icosahedral area layout (brain `user_documents/HESPERIA_ACADEMIA/`)
- **22_SPEC** — GCS + Interior Point of World View ([brain draft](https://github.com/igareosh/cursor/blob/main/user_documents/HESPERIA_ACADEMIA/HESPERIA-FORMALIZATION-GEODESIC-SPHERE-AND-INTERIOR-POINT-OF-WORLD-VIEW-v0_1.md))
- **23_SPEC** — General Thought Propagation ([brain draft](https://github.com/igareosh/cursor/blob/main/user_documents/HESPERIA_ACADEMIA/HESPERIA-FORMALIZATION-GENERAL-THOUGHT-PROPAGATION-v0_1.md))
- **Ethan ratification** — [SPEC-ETHAN-HESPERIA-METRIC-AND-DISTANCE](https://github.com/igareosh/cursor/blob/main/governance/SPEC-ETHAN-HESPERIA-METRIC-AND-DISTANCE.md)
- **Chiron entity** — [SPEC-ETHAN-CHIRON-HESPERIA-CALIBRATION-ENTITY](https://github.com/igareosh/cursor/blob/main/governance/SPEC-ETHAN-CHIRON-HESPERIA-CALIBRATION-ENTITY.md) (Status: **Accepted**, 2026-08-17) — one-man-army of Hesperia's existing operability/quality, params↔math↔corpus calibration authority, recipes, feature theorizing for the gaps
- **Dev/train boundary** — [SPEC-ETHAN-HESPERIA-DEV-TRAIN-BOUNDARY](https://github.com/igareosh/cursor/blob/main/governance/SPEC-ETHAN-HESPERIA-DEV-TRAIN-BOUNDARY.md) (Status: **Ratified**, 2026-08-17) — mode marker for the shared Felix/Gena-vs-Chiron zone; promote-gate awareness of which regime produced a change

## Concept-graph metric layer (BELL/KSI)

| Term | Qualified form | Layer |
|------|---------------|-------|
| `path_mass` | BELL `path_mass` on corridor bundles | `metric_layer=concept_graph` |
| KSI | **KSI-Inspector** (inspection tool) | `metric_layer=concept_graph` |
| KSI (score) | **KME-KSI-score** (quality metric) | engine output, not a spatial distance |

BELL `path_mass` uses edge weight W_e / resistance R_e on Floor-2 concept relations (24_SPEC §4.6, §5).
Bare "KSI" in runtime docs is ambiguous — always qualify (24_SPEC §7).

## Environment flags (metric emit)

| Variable | Default | Effect |
|----------|---------|--------|
| `HESPERIA_METRIC_EMIT` | `0` | When `1`, attach `meta.hesperia_metric` + `coordinate_fingerprint` on analyze |
| `HESPERIA_L6_PERTURBATION` | `0` | When `1`, attach `meta.layer_6` via hit-vector E(x±ε) producer |
| `HESPERIA_GCS_EMIT` | `0` | When `1`, emit static `geodesic_sphere` block (requires frozen `anchor_map_v1`) |

See 24_SPEC §10 and promotion checklist §12.
