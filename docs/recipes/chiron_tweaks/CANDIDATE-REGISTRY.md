# Chiron candidate registry — every calibratable parameter, tiered, tracked

**Purpose**: single addressable list of what's calibratable in Hesperia, what's done, what's
open now, and what needs programming/wiring before tuning it means anything. Answers "where are
we at" without re-deriving it from `BACKLOG.md`'s chronological log each session. Feeds future
`CHI-*` investigations and `params_combo/PC-*` recipes — this file names candidates, those two
do the actual work.

**Reading aid**: [STATUS-SNAPSHOT-2026-08-21.md](STATUS-SNAPSHOT-2026-08-21.md) — every named
constant, one line each, grouped by the 92 operational / 34 accommodated (gated) / 0 blocked / 18
retired / 4 sealed buckets below (post CHI-014-02 C6 key remove + CHI-015 TFP accommodation). This
file stays the source of truth; the snapshot is for a fast scan.

**Address-backwired 126 (define / calibrate / live / tweak):** [CHIRON-126-ADDRESS-MAP-2026-08-21.md](CHIRON-126-ADDRESS-MAP-2026-08-21.md) — use before any `PC-*` or numeric retune.

**Source of truth for every row**: `docs/foundations/parameter_catalog.md` (production catalog,
§0–§8), `assets/calibration/dynamics_parameter_registry.yaml` (Phase1–4Theta + Ξ, exact
ranges/defaults/`code_field`), `docs/foundations/parameter_synergies.md` (which rows are
calibrated as a set, not independently). No row here is invented — each is grep-traceable to one
of those three files.

**Owner**: Chiron. Every real move on a row here still goes through §3's thinking-map gate and
§8b's toolchain (release gate + pytest) before it counts as done — this registry tracks status,
it doesn't skip the process.

---

## Where the "60" came from, and why the real number is bigger

The original survey (CHI-002/003/004) covered **60 real candidates**, narrowly scoped to
corpus-calibration combos across two subsystems:

| Subsystem | Count | Closed as |
|---|---|---|
| KME primitives (6) + derived metrics (35) | **41** | [CHI-002](CHI-002-tfp-kme-grain-and-marker-index-gap.md) — grain default fixed (12→10), marker_index wired explicit |
| Phase1Theta (9) + Phase2Theta (9) | **18** | [CHI-003](CHI-003-a10-dominance-decay-vs-cumulative.md) → [CHI-003-01 verdict](CHI-003-01-COLOMBO-VERDICT.md) — dual-signal `areas_working`, FD constants explicitly **not** adopted |
| `dlcr_alpha` | **1** | [CHI-004](CHI-004-dlcr-alpha-dead-return-field.md) — dead return field wired |

**All 60 closed.** But that survey never touched two other real tiers: the production catalog's
own §1–§7 (never part of the 60 — a separate, already-live calibration surface), and the rest of
the Field Dynamics extension beyond Phase1/2Theta (§8's remaining groups, all currently off the
product output path). Counting those honestly:

| Tier | Count | Ready to grind now? |
|---|---|---|
| A — the original 60 | 60 | **Done** |
| B — live production catalog (§1–§7) | **42** listed; **13** (B6) **permanently retired** (CHI-B16 — replaced by Layer-9, not broken-to-fix); remainder operational / held | Config-only where still live; B6 not a tune target |
| C — Field Dynamics beyond Phase1/2Theta | **34** (was 39; C6 nested key **retired** CHI-014-02) — **all 34 accommodated 2026-08-21 (CHI-015)** | **Gated, opt-in, real.** Operator named TFP as the Class B consumer Ethan's A1 required — `hesperia.modules.tfp.field_dynamics_consumer` binds all 34 into a real, tested envelope behind `HESPERIA_TFP_FIELD_DYNAMICS` (default **off**). **Not** on `/product/interpret` by default, **not** a sealed-core merge — accommodated ≠ operational-by-default, see Tier C section below. |
| D — sealed geometry, never Chiron's | 4 | **Hard stop — not a next move.** No verify-then-propose, no wiring proposal, no feature-theorizing note. Flatly never Chiron's (sealed core geometry). |

**Operator inventory lock (2026-08-21, post CHI-B16 / CHI-013 / CHI-014-02 / CHI-015):** **92
operational** (default-live) · **34 accommodated** (Tier C C1–C5, gated opt-in via TFP Class B
consumer, `HESPERIA_TFP_FIELD_DYNAMICS` default off) · **0 blocked** · **18 permanently retired**
(13 B6 + 5 C6 nested-key hygiene) · **4 sealed** (D). C6 key remove did not improve Tier C product
reach; the separate CHI-015 wave is what did — accommodated is a real, tested, opt-in surface, not
a default-behavior change and not the same claim as "operational."

---

## Tier A — closed (the original 60)

| ID | Candidates | Status | Evidence |
|---|---|---|---|
| CHI-002 | 41 (KME 6 primitives + 35 derived) | ✅ DONE | Hesperia `4fe53ca`; grain 12→10 verified live |
| CHI-003 | 18 (Phase1Theta 9 + Phase2Theta 9) | ✅ DONE (verdict: don't adopt as-is) | Hesperia `02623ad`; `areas_working` dual signal, 7/14 real sessions differ from `areas_final` |
| CHI-004 | 1 (`dlcr_alpha`) | ✅ DONE | Hesperia `a75bc5b`; `dlcr_blend: {dlcr_merged: true, dlcr_alpha: 0.22}` verified live |

---

## Tier B — live production catalog, open now (42 candidates, 8 packs)

All of these are on the real `/product/interpret` output path today — a change here changes what
a caller sees. Config-only (YAML / `DEFAULT_CONFIG`), no programming, no API cost. Each pack
still needs: thinking-map clearance (§3), real-session validation, `calibration_release_gate.py`
+ relevant pytest before landing as a `PC-*` recipe (§5a). **Exceptions, found 2026-08-21 across
the full Tier B sweep**: B6 is **not** actually on any live output path at all — see its row and
[CHI-006](CHI-006-diagnostic-thresholds-b6-unwired-finding.md). B1 and B7 are live, but via a
*different* file/function than the one this table and `parameter_catalog.md` name as the source —
see their rows, [CHI-011](CHI-011-fgr-freshness-b7-split-finding.md) (B7, split — 2 of 4 params
live via `state_classifier.py` not `fpf_bridge`), and
[CHI-012](CHI-012-activation-floor-b1-disconnected-calibration.md) (B1 — real gate is
`clinical_bridge.py`'s own hardcoded copy, not the named YAML). B2/B3/B4/B5/B8 checked out clean
— documentation matched source exactly. Traced, not assumed, before writing any of these
caveats — the pattern across all three exceptions is the same: verify the call graph before
tuning, don't take a "live"/"CI-enforced" claim at face value just because it's written down.

| Pack | Candidates | Params | Source | Why grouped | Status |
|---|---|---|---|---|---|
| **B1 — Activation floor** | 2 | `activation_threshold`, `area_active_threshold` | `activation_calibration.yaml` → `activation_calibration.py` → `clinical_bridge.py` | Foundational — every downstream ratio's denominator depends on these. **CHI-B16-02**: wired — clinical_bridge uses calibration getters; YAML path fixed to `assets/specs/canon/`. | ✅ Wired ([CHI-012](CHI-012-activation-floor-b1-disconnected-calibration.md) → CHI-B16-02) |
| **B2 — Propagation weights** | 6 (was listed 5 — `concept_to_family_multiplier` found undocumented, no-op, until CHI-007) | `center_to_inner`, `inner_to_middle`/`middle_to_inner`, `middle_to_outer`/`outer_to_middle`, `bridge_weight`, `decay_factor` (no-op), `concept_to_family_multiplier` (no-op) | `propagation_weights.yaml` | `parameter_synergies.md` §2: `bridge_weight` × shadow-correction entropy cap is a documented pair, not independent — must move together or re-validate the shadow bound. **CHI-007 finding**: sound design-time reasoning, but the two currently run on lanes that never co-occur in one request (TFP-analyze lane vs. sealed Layer 1-10 pipeline) — not same-request enforceable today. | ✅ Reviewed, held ([CHI-007](CHI-007-propagation-weights-b2-baseline.md)) |
| **B3 — Core Math fusion/traversal** | 6 | `alpha`, `eta`, `K_max`, `lambda`, `decay`, `E_cap` | `core/math/core_math.py DEFAULT_CONFIG` | One physics set — `E0 = α·S'+(1−α)·L'` then `D=(1−λ)E+λ(EW)` over `T_steps=8`, compounding. | ✅ Reviewed, held ([CHI-009](CHI-009-fusion-traversal-b3-baseline.md)) |
| **B4 — Core Math governance penalties** | 8 | `k_amb`, `delta_gap`, `tau_core`, `k_thin`, `k_disp`, `k_guard`, `k_shadow`, `max_shadow_hops` | same | One governance-score set — each is a penalty coefficient on the same final score, tuned relative to each other, not absolute. | ✅ Reviewed, held ([CHI-010](CHI-010-governance-penalties-b4-baseline.md)) |
| **B5 — Obstacle-score weights** | 3 | `w_decay`, `w_guard_obs`, `w_shadow_obs` | same | Mathematically must sum to 1.0 — literally cannot move independently; any recipe touching one must restate all three. **CHI-008 correction**: `validate_config()`'s sum check is real but has zero callers except a manual-only self-test (`python core/math/core_math.py test`) — not actually wired into pytest CI as this cell used to claim; small follow-up flagged, not done here. | ✅ Reviewed, held ([CHI-008](CHI-008-obstacle-score-weights-b5-baseline.md)) |
| **B6 — Diagnostic / logic rule thresholds** | live Layer-9 set (was 13 orphaned in `diagnostic_rules.yaml`) | Layer-9 rules in `logic_rules.yaml` (entropy/curvature/coverage/stability + governance codes) | `logic_rules.yaml` / `sphere/logic/` | **CHI-B16-03**: retired `sphere/diagnostics` + `diagnostic_rules.yaml` as Tier-B calibratable; Layer-9 remains canonical on tfp/fingerprint/llm-audit. No interpret wire. | ✅ Retired pack / retargeted ([CHI-006](CHI-006-diagnostic-thresholds-b6-unwired-finding.md) → CHI-B16-03) |
| **B7 — FGR/Freshness calibration** | 4 | `DOMINANT_SHARE_HIGH`, `ENTROPY_DROP_SIGNIFICANT`, `STABILITY_CURRENT_THRESHOLD`, `STABILITY_STALE_THRESHOLD` | `parameter_synergies.md` §4 | Only group whose "output" is LLM narration permission, not a report number — different validation shape (narration-trust tiers, not a metric). **CHI-011 split finding**: `DOMINANT_SHARE_HIGH`/`ENTROPY_DROP_SIGNIFICANT` live via `state_classifier.py`'s own copy (sealed Layer-10), not the `fpf_bridge/constants.py` copy the docs describe; `STABILITY_CURRENT_THRESHOLD`/`STABILITY_STALE_THRESHOLD` real and tested but not reachable from any live route yet (`fpf_bridge` is `product_surface: internal`, correctly labeled, one specific reach-claim overstated). | ✅ Reviewed, held ([CHI-011](CHI-011-fgr-freshness-b7-split-finding.md)) |
| **B8 — TRIZ relation weights** | 3 | `conflict`/`negation` weight, `opposition` weight, `LOUVAIN_SEED` | TRIZ clustering config | Smallest, most isolated pack — good first grind to prove the pipeline before B1's high-blast-radius pack. | ✅ Reviewed, held ([CHI-005](CHI-005-triz-b8-relation-weights-baseline.md)) |

**Recommended grind order**: B8…B1 Tier B sweep closed 2026-08-21. **CHI-B16 (Grace→Gena)**:
B1 wired (YAML→getters→clinical_bridge); B6 retired/retargeted to Layer-9. Remaining caveat:
B7 split-doc (CHI-011) — Colombo wiki / awareness only.

---

## Tier C — Field Dynamics beyond Phase1/2Theta (34 accommodated, 5 packs + C6 retired)

**Accommodated 2026-08-21 (CHI-015)** — operator named the TFP module as the "named Class B
consumer" [CHI-013](CHI-013-tier-c-reachability-verification.md)/Ethan's SPEC said was required
to move any of this off HOLD. `hesperia.modules.tfp.field_dynamics_consumer.build_tfp_fd_param_envelope()`
binds all 34 into a real, tested envelope, gated behind `HESPERIA_TFP_FIELD_DYNAMICS` (default
**off** — gate-off returns `{_skipped: True}`, zero change to default `/product/interpret`
output). 11/11 pytest green (`tests/test_tfp_field_dynamics_gate.py`), independently re-verified
this session. Still **not** a sealed-core merge, still **not** on by default, still **not** a
numeric retune — the envelope surfaces current values honestly, doesn't move any of them.
Hesperia `1215569` (dev `origin/main` + `backup/main`).

Before this wave, verified 2026-08-21 ([CHI-013](CHI-013-tier-c-reachability-verification.md)):
C1/C2/C3/C5 all confirmed to share one real, tested, off-path profile — reachable only via
`e2e_bridge.py::run_field_dynamics_e2e_artifact()`, called only from the offline
`runtime/pipeline/run_e2e_all.py`. That offline path is now *also* exercised through the gated TFP
envelope above; the two are not mutually exclusive.

| Pack | Candidates | Params | Module | Status |
|---|---|---|---|---|
| **C1 — Phase3Theta (hex grain)** | 9 | `hex_cap`, `lambda_h`, `theta_c`, `theta_d`, `theta_p`, `mu_h`, `delta_h`, `rho_h`, `hex_hit_blend` | `hesperia.extensions.dynamics.state.Phase3Theta` | 🟡 **Accommodated** — gated TFP envelope (S-ENV), CHI-015 W2 |
| **C2 — Phase4Theta (cluster gravity)** | 3 | `gravity_epsilon`, `tau_front`, `ephemeral_cap` | same, L8 | 🟡 **Accommodated** — gated TFP envelope (S-ENV), CHI-015 W3 |
| **C3 — Ξ tension proxy** | 4 | `xi_scale`, `xi_kme_weight`, blend constants `0.35`/`0.65` | `xi_proxy.py` | 🟡 **Accommodated** — gated TFP envelope (S-ENV), CHI-015 W4. CHI-013's earlier "confirm exact reach" self-flag stays resolved: still identical profile to C1/C2/C5, this wave didn't make it "more live" than the others, all five moved together. |
| **C4 — HSPR Calibration Index** | 7 | 6 weighted components + `source_alignment_kappa` | `calibration.py` | 🟡 **Accommodated, offline only** — `run_tfp_hspr_offline_calib_job()` writes a weights report (`runtime_score: False`); explicitly **not** wired as a live product metric (Ethan rejected "HSPR as runtime score" — wrong type, meta-calibration ≠ per-request metric). CHI-015 W5. |
| **C5 — Semantic Field v1** | 11 | `alpha`, `beta`, `gamma`, `delta`, `mu`, `dt`, `epsilon`, `tau`, `resistance_uniform`, `production_clip`, `signed_source_experimental` | `equations.py`/`semantic_field_v1.py` | 🟡 **Accommodated** — gated TFP envelope (S-ENV) from live `SemanticFieldParamsV1`, CHI-015 W6 |
| **C6 — `profiles_v1.json` hex reference** | 5 | `alpha_H`, `beta_H`, `gamma_H`, `delta_H`, `dt` | removed from `profiles_v1.json` | ⛔ **Retired CHI-014-02** (Felix): nested `hex_field_reference` deleted. File siblings remain live for C5 via `semantic_field_params_from_profile()`. Stays retired — CHI-015 didn't touch it. |

**What "accommodated" does and doesn't mean**: the 34 are real, tested, and reachable through an
explicit opt-in surface (`HESPERIA_TFP_FIELD_DYNAMICS=1`) — genuinely more than Tier C had before
today. It does **not** mean they're on `/product/interpret` by default, part of the sealed core, or
tuned to new values — none of that happened, and Grace's hard refusals (no Class A merge, no
silent default-interpret dump, no retune until a surface actually consumes them) still hold for
every one of these 34.

---

## Tier D — sealed, never Chiron's (4 candidates) — **hard stop**

**Not a next move.** Unlike Tier C (off-path, real code, verify-then-propose / engineering gate),
Tier D is **sealed core geometry** that everything else sits on (288-family grid, hex counts,
grain defaults — CHI-002 only touched the *edge* of grain wiring, not these constants). There is
**no** verify-then-propose motion, **no** wiring proposal, **no** feature-theorizing note. Chiron
spec boundary excludes it outright: not a documented-parameter toggle — flatly **never Chiron's**.

| Params | Source | Why excluded |
|---|---|---|
| `AREAS=12`, `FAMILIES_PER_AREA×AREAS=288`, `HEXES_PER_FAMILY×TOTAL_FAMILIES`, `SIDES_PER_HEX=6` | Geometry constants, `parameter_catalog.md` §0 | The fixed shape every Sigma check validates against. Changing any of these invalidates the sealed contract — Felix/Gena territory **if ever revisited**, and **only** as an architecture decision, **not** a calibration one. |

---

## Bundle/pack execution notes

- **API cost**: none of Tier B/C's *tuning* work needs external API calls — these are YAML/config
  value changes, validated through the existing real-session corpus + `calibration_release_gate.py`
  + pytest, same toolchain as CHI-002/003/004. API cost only re-enters if a pack's validation
  needs *new* real-session data or a dict-alignment-style LLM pass (the gpt-5-mini corpus work in
  `BACKLOG.md` Phase 4c is the precedent/cost model if that's ever needed here: ~$1.39 for an
  882-call run, real pricing fetched live, not estimated).
- **Programming**: Tier C's wiring tasks are real engineering (Felix/Gena, `core/layers/`-adjacent)
  before any Tier-C pack becomes calibratable — Chiron's own boundary (§5: "may propose, not
  implement alone: new layer logic"). C6 is a deletion candidate, not a wiring one.
- **Bundling into packs, not 145 individual moves**: matches `parameter_synergies.md`'s own
  finding that several of these are calibrated as a set (B2, B5 by construction, B3/B4 as physics/
  governance sets) — a `PC-*` recipe per pack, not per parameter, is both more honest about what's
  actually independent and less total grind.
- **No row here is "done" until it has a `PC-*` recipe with validation evidence** (per
  `params_combo/README.md` §Shape) or a `CHI-*` investigation write-up, same bar as the original 60.

---

## Status legend

✅ DONE · 🔲 Not started · 🟡 Accommodated (gated, opt-in — real and tested, not default-live) ·
⛔ Retired (permanent, not a tune target) · 🔒 Sealed (never Chiron's)

---

SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-20 | candidate registry, Tier A closed (60/60), Tier B open (42), Tier C blocked on wiring (39), Tier D excluded (4)
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | CHI-015 verified + committed (Hesperia `1215569`) — Tier C's 34 (C1–C5) accommodated under a gated TFP Class B consumer, default off; inventory now 92 operational / 34 accommodated / 0 blocked / 18 retired / 4 sealed
