# Parameter synergies, and what value actually reaches the LLM

The corner docs explain why each module exists. This file answers a narrower, sharper question:
**when two parameters from different stages are combined, what do you get that neither gives you
alone — and what, specifically, is handed to the LLM as a result?** Every number below is read
directly from the repo, not paraphrased from a spec.

## 1. The clearest synergy case study: KME's 35 metrics are entirely about which primitives combine

`corners/kme.md` already documents the six bounded primitives (`LD`, `COH`, `NC`, `PR`, `PV`,
`CI`) and that all 35 derived metrics are products/ratios over them. What's worth pulling out
explicitly: **which pairs get combined, and how often**, because the frequency itself is a
judgment about which synergies the system considers meaningful.

`COH × LD` (Coherence × LogicalDensity) appears, directly or as a factor, in **six** of the 35
metrics (`KDI`, `SCS`, `TCI`, `KNS`, `KDI2`, `KVI`, `ASS`) — by far the most reused pair. The
reason this specific combination earns that much reuse: density alone (`LD`) cannot distinguish "a
lot of tightly interconnected, on-topic structure" from "a lot of noisy, unrelated connections,"
and coherence alone (`COH`) cannot distinguish "one idea stated densely" from "one idea stated
once." Multiplying them filters for *exactly* the case that matters — dense **and** coherent — and
zero-floors any case that's one without the other (a single low factor drags the product toward
zero, by construction, since both inputs are pre-clamped to `[0, 1]`).

`PR` (PropagationRadius) appears almost exclusively as a **denominator** (`KCI = LD/PR`,
`KE = PR/LD`, `KSI = COH·LD/PR`, `KPS = COH/PR`) rather than a numerator alongside the others. The
pattern this encodes: PR measures *cost* (how far activation had to spread), so every metric that
divides by it is asking an efficiency question — "how much of [density/coherence/whatever] was
achieved per unit of spreading effort" — while the handful of metrics that multiply by PR instead
(`TDS = PR·LD`, `KDI2 = LD·PR·COH`) are explicitly asking the opposite question, "how much raw
reach was involved," with no efficiency normalization. The same primitive plays a structurally
different role (cost-in-denominator vs. magnitude-in-numerator) depending on which question a
given derived metric is built to answer — this is the synergy: **the meaning of `PR` is defined by
what it's combined with, not by its own value.**

## 2. Cross-stage synergy: propagation weights × shadow correction

`specs/canon/propagation_weights.yaml` fixes real numbers for how activation spreads:

| Edge type | Weight |
|---|---|
| `center_to_inner` | 0.25 |
| `inner_to_middle` / `middle_to_inner` | 0.18 |
| `middle_to_outer` / `outer_to_middle` | 0.12 |
| `bridge_weight` (cross-area) | 0.22 |

The combination worth noticing: `bridge_weight` (0.22) sits *between* the innermost zone weight
(0.25) and the next ring out (0.18) — cross-area "bridge" edges are deliberately weighted almost as
strongly as the most local in-area spread, not suppressed toward zero. Combined with shadow
correction's entropy cap (`corners/shadow_correction.md`), this is a specific, tunable trade-off:
a high bridge weight pushes more cross-area activation into the field, which raises entropy faster,
which gives the shadow-correction stage more work to do capping it. Turning bridge weight up
without separately re-validating the shadow correction bound would silently change how much
cross-area "spillover" the system tolerates before correction kicks in — the two parameters are
calibrated as a pair, not independently, even though they live in different YAML files and
different modules.

## 3. Guard combination: Sigma AND Gamma, never Sigma alone

`specs/canon/theta_governance_rules.yaml`'s `THETA_001` is a literal AND over two independently
computed booleans:

```yaml
condition:
  all:
    - fact: sigma_passed
      op: eq
      value: true
    - fact: gamma_passed
      op: eq
      value: true
action: approve_canonical
```

Neither guard's pass/fail alone is sufficient for `approve_canonical` — a structurally valid
artifact (Sigma) produced by an unsound execution (Gamma fail) is exactly as disqualifying as a
malformed artifact produced by a sound execution. The combination *is* the eligibility test; either
parameter in isolation answers a narrower question than the one Theta needs answered.

## 4. The worked example: how two parameters jointly decide what the LLM is allowed to trust

This is the most concrete answer to "what is the input value to the LLM." `sphere/fpf_bridge/constants.py`
defines a calibrated trust table — not a single confidence number, but an FGR triple
(`formality, scope, reliability`) per L9 rule type, in two tiers:

| Rule type | FGR (high tier) | FGR (low tier) | Gating parameter | Threshold |
|---|---|---|---|---|
| `dominant_area` | (0.9, 0.7, 0.9) | (0.7, 0.5, 0.7) | `share` | `DOMINANT_SHARE_HIGH = 0.35` |
| `entropy_drop` | (0.8, 0.6, 0.8) | (0.6, 0.4, 0.6) | `delta_entropy` | `ENTROPY_DROP_SIGNIFICANT = 0.15` |
| `tension_increase` | (0.7, 0.5, 0.7) | (0.5, 0.4, 0.5) | — | (type-only, no magnitude gate) |
| `propagation_spread` | (0.6, 0.8, 0.6) | (0.5, 0.6, 0.5) | — | (type-only) |
| `dominance_transition` | (0.8, 0.6, 0.5) | (0.6, 0.4, 0.4) | — | (type-only) |

`evidence_mapper.py`'s `_rule_fgr` shows the actual combination: for a `dominant_area` rule, the
FGR tier handed to the LLM is selected by checking `share >= 0.35` — i.e., **the surface-logic
rule's own magnitude parameter decides how much to trust the surface-logic rule's own claim.** A
rule that fired on a 36%-dominant area is handed to the LLM as evidence with `reliability=0.9`; the
identical rule type firing on a 20%-dominant area gets `reliability=0.7` — same rule, same claim
text, different trust metadata, because the underlying magnitude differed.

Independently, `map_stability_to_freshness` takes a **dynamics-logic** parameter
(`stability_index`, from `corners/propagation_dynamics.md`'s trajectory tracking) and maps it to a
`Freshness` enum — `CURRENT` above 0.7, `EXPIRED` below 0.3, `STALE` between — and this single
value is applied to **every** evidence primitive built from that pipeline run's triggered rules.

**The combination that actually reaches the LLM, per piece of evidence, is therefore the product of
two independent computations from two different stages**: (surface-logic rule type × its own
magnitude) → FGR, and (dynamics-logic stability, computed once per run) → Freshness, attached
jointly to every evidence primitive in that batch. A highly-confident-looking rule (`reliability=0.9`)
from a run whose stability is `EXPIRED` is not silently treated as trustworthy-and-current — the
LLM substrate receives both signals and the state-graph's gates (`corners/fpf_bridge.md`) can
require both to clear before allowing a transition. Neither parameter alone tells the LLM what it
needs to know; the pair does.

## 5. What this means for "what is genuinely sellable"

`corners/triz_extension.md` already argues that exported decision-intelligence products are the
sellable surface over an otherwise-invisible determinism core. The FGR calibration table above is
a second, different kind of sellable asset: **it is encoded judgment, not a generic algorithm.**
Anyone can call an LLM with a RAG-retrieved passage and a generic confidence score; deciding that
a "dominant area" claim deserves `reliability=0.9` only above a 35% share, and exactly `0.7` below
it, is a specific, calibrated, defensible position about how much a structural signal of a given
strength should be allowed to influence downstream language — the kind of thing that requires
domain experience with the actual failure modes (false-confident narration, premature certainty)
to get right, and that a competitor copying the *architecture* (bridge a deterministic pipeline to
an LLM) would still have to re-derive from scratch by making the same mistakes this calibration
table was presumably tuned to avoid.

## 6. TFP DLCR structural dict pin: two env gates, only one path when both are set

`runtime/shipping/analyze_profile.py::apply_analyze_profile_defaults(profile="tfp")` sets two
env vars together, and neither one alone gets you real structural DLCR concept resolution:

- `HESPERIA_DLCR_STRUCTURAL=1` — turns the structural-DLCR call path *on* inside
  `sphere/router/engine_analyze_bridge.py::run_engine_analyze()` (gated via
  `hesperia/system/capabilities.py`).
- `HESPERIA_CALIB_DICT_VERSION=v0_6_0_clr_v052_5` — tells `hesperia/engine/calibration_dict_paths.py`
  which dict pack to resolve against; unset, it silently falls through to the much smaller
  `assets/data/engine_dynamics_v060/dict_{a,b}/*` stack.

Set `HESPERIA_DLCR_STRUCTURAL` without pinning the dict version and DLCR genuinely runs — against
the wrong dictionary, with no error. Pin the dict version without the structural flag and it's
never consumed at all, because the call path that reads it doesn't execute. Only both together
route TFP analyze onto the sealed pack (`assets/calibration/dicts/v0_6_0_clr_v052_5/`: 283 Dict B
concepts, 10155 Dict A token entries → 135 B ids, 24000 Dict C phrases → 212 B ids). Empirically
verified (2026-08-18): `concept_weights` count 2→6 and 4→7, `lexical_hits_accepted` 2→10 and 3→12,
same two RU clinical test statements, pin applied vs. not. Full recipe:
`docs/recipes/params_combo/PC-001-tfp-dlcr-dict-pin-full-stack.md`.

## 7. TRIZ topology activation: which cluster source is behind `--with-topology` decides whether the uniformity gate means anything

`hesperia/extensions/triz/topology_activation_pipeline.py::run_topology_triz_activation()` needs a
`concept_clusters` list to build family-pair weights from. Two different sources can supply it,
and they are not interchangeable inputs to the same downstream check:

- Real TRIZ `innovation_clusters` (from `--with-triz`, `08_triz_complete.json`) — genuine
  concept-level clustering.
- `synthetic_clusters_from_coactivation_edges()` — a coarse union-find fallback used only when
  `--with-triz` wasn't also passed, lumping many families into one or two giant components from
  raw co-occurrence alone.

`family_weights_sparsify.py::build_sparse_family_weights()`'s anti-degeneracy check
(`UNIFORMITY_FRAC_MAX = 0.30` — no single rounded weight value may cover more than 30% of edges)
is meaningful *evidence* against the real-cluster source and largely *noise* against the
synthetic-fallback source, because the fallback's coarse lumping structurally produces a narrower
weight distribution regardless of the input text. Running `--with-topology` alone (as a
standalone diagnostic, without `--with-triz`) reliably trips this gate on real fixtures —
`uniformity:0.6680>0.3`, confirmed 2026-08-18 on the tracked `tests/fixtures/tfp/input.txt`
fixture, `errors: []` once `--with-triz` is added back. This is not a calibration regression to
chase; it's a read on which clustering source is live, and `--with-topology`'s own CLI now warns
about it (`tools/gena_tfp_bundle_run.py`) so this doesn't have to be re-derived from a traceback
next time. See `corners/triz_extension.md` for what the real cluster path is for.

## 8. Truth-point grounding: literal family-match and corpus-redundancy are different evidence types, and combining them is what makes "mostly true, with exceptions" operational

§6/§7 above are both about whether an existing check is reading the right signal. This one adds a
genuinely new signal rather than fixing an existing one. Starting premise (operator, 2026-08-18):
the TFP research corpus (`tfp_corpus`, Postgres — 274 files / 49,322 chunks, Klein/Bion/Kernberg/
Clarkin-Yeomans et al.) is real, mostly-authoritative published clinical theory, not noise — so
when the family-grain grounding check (§0 of this file's own PC-001 lineage, and
`SPEC-ETHAN-TFP-CORPUS-POSTGRES.md`) reports a contradiction pair as ungrounded, that can mean two
different things: the concept genuinely isn't present, *or* it's present but phrased differently
than the dict pack's exact family/area match expects. Those need different evidence, not one gate
number.

- **`L`** (existing): the family-grain literal check itself — did any concept in the same Dict-B
  family as this pair get a direct lexical hit. Binary, cheap, already gates `internal_review`.
- **`S`** (new): does the *concept's own label* have real support somewhere in the corpus text,
  independent of whether the specific input segment happened to use that exact wording.
  `hesperia/modules/tfp/data/tfp_v1/postgres/corpus_grounding.py::corpus_support()` — Russian
  full-text search (`ts_rank_cd`, not raw trigram similarity: trigram was tried first and was
  ~100x slower for no accuracy gain, see that file's own docstring for the `EXPLAIN ANALYZE`
  evidence) against `tfp_corpus`.
- **`W`** (new): how many *independent source documents* corroborate that support. A concept
  showing up across several different books/authors in the corpus is functionally more
  established than one traceable to a single obscure mention — this lets the corpus's own
  redundancy stand in for an authority judgment nobody has to assert by hand.
- **`T = max(L, S·W)`**: deliberately a ceiling-raise, not a blend. A pair the literal check
  already grounds (`L=1`) stays grounded regardless of what the corpus channel says — this can
  only add confidence to an otherwise-ungrounded pair, never subtract it from a grounded one.

Empirically (2026-08-18, real sessions, not synthetic fixtures): `1-11-09-2023`
(`truth_point_accumulation=0.4605`, 46/340 pairs rescued) vs. `14-12-2023`
(`truth_point_accumulation=0.0828`, 74/391 pairs rescued, but `zero_lexical_evidence_share=0.928`
to begin with) — the metric tracks the same direction as the underlying grounding gap across two
genuinely different real sessions, not a constant. Honest limit, not yet resolved: raw
`ts_rank_cd` magnitudes run small (~0.001–0.4 observed), so `S·W` rarely approaches 1.0 — today
this is a real, differentiated diagnostic signal, not yet strong enough to flip a gate verdict on
its own. Recipe: `docs/recipes/chiron_tweaks/CHI-001-tfp-corpus-truth-point-grounding.md`.

## Relationship to neighboring corners

- Builds on, does not replace, `corners/kme.md` (primitive/derived-metric definitions),
  `corners/propagation_dynamics.md` and `corners/shadow_correction.md` (weight/entropy parameters),
  `corners/guards.md` (Sigma/Gamma/Theta), and `corners/fpf_bridge.md` (FGR, Freshness, the bridge
  itself).
- `provenance.md` covers where FGR's *theory* comes from (FPF Part B.3); this file covers how
  Hesperia's own calibration *populates* that theory with specific, load-bearing numbers.
