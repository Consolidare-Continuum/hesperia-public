# CHI-005 — TRIZ relation weights (B8): thinking-map → release-gate → pytest baseline, verdict: hold

## 1. Task/goal

First real grind on `docs/recipes/chiron_tweaks/CANDIDATE-REGISTRY.md`'s Tier B, pack **B8 — TRIZ
relation weights** (3 candidates: `conflict`/`negation` relation weight, `opposition` relation
weight, `LOUVAIN_SEED`), chosen as the registry's own recommended first pack — smallest, most
isolated, meant to prove the full toolchain (thinking-map clearance → `calibration_release_gate.py`
→ pytest) end-to-end before grinding the bigger/riskier packs (B1's activation floor, B3/B4's
physics/governance sets). Question this pack actually poses: is there real-session evidence that
`conflict`/`negation=1.0`, `opposition=0.85`, or `LOUVAIN_SEED=42` should move from their current
values, or do they hold as calibrated?

## 2. Where the three candidates actually live

| Parameter | File | Line | Current value |
|---|---|---|---|
| `conflict` relation weight | `hesperia/extensions/triz/contradiction_engine.py::_REL_WEIGHT` | 15 | `1.0` |
| `negation` relation weight | same | 16 | `1.0` |
| `opposition` relation weight | same | 17 | `0.85` |
| `LOUVAIN_SEED` | `hesperia/extensions/triz/novelty_engine.py` | 21 | `42` |

`_REL_WEIGHT` is consumed at `contradiction_engine.py:62` — `w = _REL_WEIGHT.get(rt, 1.0) *
float(r.weight)`, one multiplier per typed relation, folded into each contradiction pair's raw
score before it ever reaches a named output field (confirmed empirically in §5 — no
`relation_type` survives to `12_input_concept_contradictions_classified.json`, so a weight change
is only observable by re-running the full pipeline and diffing aggregate metrics, not by reading a
single field). `LOUVAIN_SEED` seeds `networkx.community.louvain_communities()` at
`novelty_engine.py:147` — a modularity-maximization community-detection call whose only role for
the seed is deterministic tie-breaking, not signal.

Neither lives in a calibration YAML — both are plain Python module-level constants, but still
documented, existing, catalogued parameters per `parameter_catalog.md` §7 (`conflict`/`negation`
= 1.0, `opposition` = 0.85, `LOUVAIN_SEED` = 42, matching source exactly), so still inside
Chiron's write-access boundary (spec §5: "documented parameter toggle").

## 3. §3 thinking-map gate (mandatory, run before touching anything)

`cursor-fpf-test-mcp`, `scope="core"` (no Hesperia-specific `user-extension` domain map exists yet
— confirmed via `list_thinking_maps`, only `team_ops`/`cluster_ops`/`eod_ops`/`susanin_ops` are
registered). Built a `SemanticMap` with one context (`hesperia_calibration`), three
`EvidencePrimitive`s (wiki-confirmed-live status, pytest baseline green, no documented
cross-parameter synergy for B8), one `GatePrimitive` requiring all three, one `TransitionPrimitive`
(`reviewing` → `cleared_for_release_gate`) gated on that evidence. `attempt_transition()`:
**`OutcomeKind.CONTINUE`**, zero validation errors, zero missing evidence. `get_audit_gaps()`
checked afterward — the returned backlog (R01–R57) is about the `fpf_thinking_map` library's own
fidelity to the FPF spec, nothing in it restricts or flags config-only Tier-B parameter review.
Move is CONTINUE-legal per §3.

## 4. Wiki-confirmed live status (mandatory before any calibration decision, spec §8a)

`hesperia-wiki` MCP, both queried directly (not assumed):

- **"Relation weights (conflict/opposition)"** — `LIVE_SUCCESSOR`, `needed_by:
  contradiction_pressure -> tension_energy`. On the real path.
- **"Louvain communities (seed 42)"** — `BEYOND` (shipped in LIVE, no Java-corpus ancestor),
  `needed_by: contradiction_pressure -> tension_energy`. Same real path.

Both real, both live, both worth the review. No wiki gap to report to Colombo for this pack
(unlike the TFP router lane the deployment map flagged earlier).

## 5. Baseline evidence — real session run against current defaults

`parameter_synergies.md` has no entry for B8 (grepped — zero hits for `TRIZ`/`conflict`/
`opposition`/`louvain` naming a must-move-together set), unlike B2/B5. So unlike PC-001, this pack
has no combined-parameter rationale to establish — each of the three can, in principle, move
independently. Before considering any move, ran the toolchain fresh against the current defaults:

```
HESPERIA_DLCR_STRUCTURAL=1 HESPERIA_CALIB_DICT_VERSION=v0_6_0_clr_v052_5 \
  python tools/gena_tfp_bundle_run.py -i tests/fixtures/tfp/input.txt \
  -o outputs/tfp/runs/chi005_b8_baseline --with-triz --with-topology \
  --gate-profile internal_review
```

Real tracked clinical fixture (`tests/fixtures/tfp/input.txt`, the same one PC-001 used), full
pipeline, real TRIZ activation (`--with-triz`, not the synthetic coactivation fallback — see
`parameter_synergies.md` §7 on why that distinction matters for this exact code path).

**Result**: `11_calibration_release_gate.json` → `pass: true`, `consistency_score_observed: 1.0`,
every check green (`contradiction_overproduction_guard`, `contradiction_grounding_zero_lex_share`
0.483871, `contradiction_grounding_inferred_share` 0.078853, `json_schema_validation`, etc.) —
`internal_review` profile.

Real numbers this run produced, current B8 defaults in effect:

| Metric | Value | Source |
|---|---|---|
| `contradiction_count` | 279 | `12_input_triz_metrics_v1.json` |
| `contradiction_density` | 0.001187 | same |
| `mean_contradiction_score` | 0.107969 | same |
| `universe_concept_count` | 686 | same |
| Innovation clusters (Louvain) | 204 | `12_input_innovation_clusters_enriched.json`, `clusters` length |
| `avg_graph_degree` | 6.469388 | `12_input_triz_dynamics.json` |
| `area_coverage` | 0.2 | same |

Baseline pytest (pre- and re-confirmed post-review, no code touched): `tests/triz/test_triz_pipeline.py`
+ `tests/test_triz_topology_activation_pipeline.py` + `tests/test_field_dynamics_triz_signal.py` —
**13 passed**, 0 failed.

## 6. Verdict: hold at current defaults

No real-session evidence surfaced in this pass that points to a specific different value for any
of the three:

- **`conflict`/`negation` = 1.0 vs `opposition` = 0.85`**: the 0.85 discount is a deliberate,
  already-documented design choice (`parameter_catalog.md` §7: "opposition is treated as real but
  slightly less certain tension than direct conflict/negation") — not an unexamined default. Moving
  it needs a real question ("is opposition systematically over/under-counted relative to direct
  conflict in real TFP contradiction pairs") that this pass didn't find grounds to ask; the gate
  passing cleanly at the current ratio is confirming evidence, not proof the ratio is optimal.
- **`LOUVAIN_SEED` = 42**: a reproducibility seed, not a signal parameter — Louvain community
  detection's seed only controls tie-breaking during modularity maximization, so changing it would
  reshuffle which near-equally-good partition gets picked on ties, not improve cluster quality.
  Nothing in the registry, the wiki page, or this session's run gives a reason to touch it; the
  page's own notes describe the seed's entire purpose as reproducibility, which a fixed value
  already satisfies.

**Closing this pack as reviewed, not as tuned.** Matches CHI-003's precedent: a real
investigation, full toolchain run, evidence gathered, and an honest "hold" verdict is a legitimate
close — not every pack needs a numeric change to count as done, and inventing one without
real-session justification would be worse than holding.

## 7. Config

No change. Current values remain: `_REL_WEIGHT = {"conflict": 1.0, "negation": 1.0, "opposition":
0.85}` (`contradiction_engine.py:14-18`), `LOUVAIN_SEED = 42` (`novelty_engine.py:21`).

## 8. Invocation (for the next Chiron session that wants to actually test a B8 move)

If a future pass has a concrete hypothesis (e.g., real evidence that opposition-type
contradictions under- or over-fire relative to conflict/negation), the reproducible comparison
path is: edit `_REL_WEIGHT`/`LOUVAIN_SEED` directly (documented-parameter toggle, in Chiron's
write-access boundary per spec §5), re-run the exact command in §5 against the same fixture,
diff `12_input_triz_metrics_v1.json` + `12_input_innovation_clusters_enriched.json` cluster count
before/after, confirm `11_calibration_release_gate.json` still passes, confirm the same 13 pytest
still green. `tools/tfp_param_sweep.py` does not apply here (it drives env/flag combos, not
in-source Python constants) — a direct edit/run/diff/revert cycle is the right shape for this
pack, unlike PC-001's env-var sweep.

## 9. Rollback

N/A — no change made.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | B8 reviewed via full thinking-map/release-gate/pytest toolchain, verdict: hold at current defaults, first Tier B pack closed
