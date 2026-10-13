# Chiron candidate registry — status snapshot, 2026-08-21

Full state of every named constant in `CANDIDATE-REGISTRY.md`, one line each, as of the CHI-B16 +
CHI-013 + CHI-014 + CHI-015 waves closing. Point-in-time snapshot, not a live feed — re-verify
anything load-bearing if it's been more than a few days. Source of truth stays
`CANDIDATE-REGISTRY.md`; this file is a reading aid, not a second registry.

**Totals: 148 named constants** (145 original + 3 found) — **92 operational · 34 accommodated
(gated, opt-in) · 0 blocked · 18 retired · 4 sealed** (post CHI-014-02 C6 hygiene + CHI-015 TFP
accommodation).

| Bucket | Count | Meaning |
|---|---|---|
| ✅ Operational | 92 | Live, correctly wired, calibratable now, **on by default** |
| 🟡 Accommodated | 34 | Real, tested, reachable via an explicit opt-in gate (`HESPERIA_TFP_FIELD_DYNAMICS`, default **off**) — **not** on by default, **not** a sealed-core merge (Tier C C1–C5, CHI-015) |
| 🚧 Blocked | 0 | Nothing left in this bucket — Tier C's last blocked items (C1–C5) moved to accommodated 2026-08-21 |
| ⛔ Retired | 18 | 13 B6 diagnostics + 5 C6 `hex_field_reference` (CHI-014-02) |
| 🔒 Sealed | 4 | Never Chiron's — geometry the whole system is built on |

---

## Tier A — closed (60) ✅ all operational (calibrated)

| ID | Candidates | Verdict | Evidence |
|---|---|---|---|
| CHI-002 | 41 (KME 6 primitives + 35 derived) | Grain default fixed 12→10, verified live | `4fe53ca` |
| CHI-003 | 18 (Phase1Theta 9 + Phase2Theta 9) | Dual-signal `areas_working` shipped; FD constants explicitly not adopted | `02623ad` |
| CHI-004 | 1 (`dlcr_alpha`) | Dead-return-field fixed, blend verified live | `a75bc5b` |

## Tier B — production catalog (45: 42 original + 3 found)

| Pack | Params | Count | Status | Notes |
|---|---|---|---|---|
| **B1** — Activation floor | `activation_threshold`, `area_active_threshold` | 2 | ✅ Operational | Was disconnected (real gate = `clinical_bridge.py` hardcoded copy, YAML did nothing) — **wired today** ([CHI-012](CHI-012-activation-floor-b1-disconnected-calibration.md) → [CHI-B16-02](../../../operational/assignments/reports/GENA-CHI-B16-CLOSEOUT-2026-08-21.md), Hesperia `b29aab4`) |
| **B2** — Propagation weights | `center_to_inner`, `inner_to_middle`/`middle_to_inner`, `middle_to_outer`/`outer_to_middle`, `bridge_weight`, `decay_factor`, `concept_to_family_multiplier` | 6 | ✅ Operational | 4 live/load-bearing, 2 no-op by design (`decay_factor`, `concept_to_family_multiplier` — reserved slots, not bugs) ([CHI-007](CHI-007-propagation-weights-b2-baseline.md)) |
| **B3** — Core Math fusion/traversal | `alpha`, `eta`, `K_max`, `lambda`, `decay`, `E_cap` | 6 | ✅ Operational | Clean — doc matched source exactly ([CHI-009](CHI-009-fusion-traversal-b3-baseline.md)) |
| **B4** — Core Math governance penalties | `k_amb`, `delta_gap`, `tau_core`, `k_thin`, `k_disp`, `k_guard`, `k_shadow`, `max_shadow_hops` | 8 | ✅ Operational | Clean, confirmed twice (this session + a prior 2026-08-04 wiki cross-check) ([CHI-010](CHI-010-governance-penalties-b4-baseline.md)) |
| **B5** — Obstacle-score weights | `w_decay`, `w_guard_obs`, `w_shadow_obs` | 3 | ✅ Operational | Live and correct; "CI-enforced sum=1.0" claim corrected (real check, but only reachable via manual self-test, not pytest) ([CHI-008](CHI-008-obstacle-score-weights-b5-baseline.md)) |
| **B6** — Diagnostic thresholds | `ultra_sparse_coverage_threshold`, `excessive_jump_threshold`, `transition_concentration_threshold`, `entropy_threshold`, `coverage_threshold`, `dominant_area_share_threshold`, `unique_areas_max`, `stability_high_threshold`, `curvature_threshold`/`severe_curvature_threshold`, `jump_rate_threshold`/`severe_jump_rate_threshold`, `low_stability_threshold` | 13 | ⛔ **Retired** | Zero live callers, zero tests, ever — not broken-to-fix, `sphere/diagnostics/` deprecated outright ([CHI-006](CHI-006-diagnostic-thresholds-b6-unwired-finding.md) → [CHI-B16-03](../../../operational/assignments/reports/GENA-CHI-B16-CLOSEOUT-2026-08-21.md)). Real live diagnostics = Layer-9 `logic_rules.yaml`, a separate system not in this count. |
| **B7** — FGR/Freshness calibration | `DOMINANT_SHARE_HIGH`, `ENTROPY_DROP_SIGNIFICANT`, `STABILITY_CURRENT_THRESHOLD`, `STABILITY_STALE_THRESHOLD` | 4 | ✅ Operational | Split: 2 live via `state_classifier.py` (sealed Layer-10), 2 real/tested but internal-only (`fpf_bridge`, correctly labeled `product_surface: internal`) — no fix needed, doc corrected ([CHI-011](CHI-011-fgr-freshness-b7-split-finding.md)) |
| **B8** — TRIZ relation weights | `conflict`/`negation` weight, `opposition` weight, `LOUVAIN_SEED` | 3 | ✅ Operational | Clean, held at defaults ([CHI-005](CHI-005-triz-b8-relation-weights-baseline.md)) |

**Tier B total: 32 operational + 13 retired = 45.**

## Tier C — Field Dynamics (34 accommodated + C6 retired) 🟡

**2026-08-21 (CHI-015)**: operator named the TFP module as the Class B consumer required to move
off HOLD. `hesperia.modules.tfp.field_dynamics_consumer.build_tfp_fd_param_envelope()` binds all
34 into a real, tested, gated envelope — `HESPERIA_TFP_FIELD_DYNAMICS`, default **off**.
11/11 pytest green, independently re-verified this session. Hesperia `1215569`.

| Pack | Params | Count | Status | Notes |
|---|---|---|---|---|
| **C1** — Phase3Theta (hex grain) | `hex_cap`, `lambda_h`, `theta_c`, `theta_d`, `theta_p`, `mu_h`, `delta_h`, `rho_h`, `hex_hit_blend` | 9 | 🟡 Accommodated | S-ENV pack, gated envelope. Was `run_e2e_all.py`-only; still real+tested, now also reachable via the gate. |
| **C2** — Phase4Theta (cluster gravity) | `gravity_epsilon`, `tau_front`, `ephemeral_cap` | 3 | 🟡 Accommodated | Same shared entrypoint as C1, same gated envelope. |
| **C3** — Ξ tension proxy | `xi_scale`, `xi_kme_weight`, blend `0.35`/`0.65` | 4 | 🟡 Accommodated | CHI-013's "confirm exact reach" self-flag stays resolved — moved together with C1/C2/C5, not ahead of them. |
| **C4** — HSPR Calibration Index | 6 weighted components + `source_alignment_kappa` | 7 | 🟡 Accommodated, offline only | `run_tfp_hspr_offline_calib_job()` writes a weights report, `runtime_score: False`. Deliberately **not** a live product metric — Ethan explicitly rejected that option (wrong type). |
| **C5** — Semantic Field v1 | `alpha`, `beta`, `gamma`, `delta`, `mu`, `dt`, `epsilon`, `tau`, `resistance_uniform`, `production_clip`, `signed_source_experimental` | 11 | 🟡 Accommodated | S-ENV pack from live `SemanticFieldParamsV1` defaults. |
| **C6** — `profiles_v1.json` hex reference | `alpha_H`, `beta_H`, `gamma_H`, `delta_H`, `dt` | 5 | ⛔ **Retired** | Nested key **removed** CHI-014-02 (Felix). Stays retired — CHI-015 didn't touch it. |

**What accommodated does *not* mean**: none of the 34 are on `/product/interpret` by default, none
are sealed-core, none were retuned. The gate is off unless someone explicitly sets
`HESPERIA_TFP_FIELD_DYNAMICS=1` — Grace's hard refusals (no Class A merge, no silent
default-interpret dump, no retune until a surface actually consumes them) all still hold.

Path: [CHI-013](CHI-013-tier-c-reachability-verification.md) (verify) →
[SPEC-ETHAN-CHI-013](../../../operational/assignments/reports/SPEC-ETHAN-CHI-013-TIER-C-WIRING-DESIGN-2026-08-21.md)
(propose, A1 recommended) → [CHI-014](../../../operational/assignments/chiron-inventory/SPEC-ETHAN-CHI-014-OPEN-FEASIBLE-2026-08-21.md)
(C6 hygiene only, C1–C5 still refused that wave) →
[GRACE-TRIAGE-CHI-015](../../../operational/assignments/chiron-inventory/GRACE-TRIAGE-CHI-015-TFP-ACCOMMODATE-TIER-C-34-2026-08-21.md)
(operator names TFP as consumer, opens A1 for real) →
[CHI-015-DRAIN-CLOSEOUT](../../../operational/assignments/chiron-inventory/CHI-015-DRAIN-CLOSEOUT-2026-08-21.md)
(Felix implements, Ava/Noah test, Sophia/Daniel review, Grace closes).

## Tier D — sealed geometry (4) 🔒 never Chiron's

| Params | Why |
|---|---|
| `AREAS=12`, `FAMILIES_PER_AREA×AREAS=288`, `HEXES_PER_FAMILY×TOTAL_FAMILIES`, `SIDES_PER_HEX=6` | The fixed shape every Sigma check validates against. Felix/Gena territory only, and only as an architecture decision, never a calibration one. |

**Never Chiron’s three motions (CHI-016-51..59):** no tune · no verify-then-propose · no §5b feature-theorizing. Grain-10 ≠ `AREAS=10`. Coordinate system — not inputs.

**CHI-016 first-class return (2026-08-21):** Layer-9 on `/product/interpret` (not B6 `run_diagnostics`); opt-in TFP-FD via flag+`HESPERIA_TFP_FIELD_DYNAMICS`; live `hspr_index` honesty; B1 SoT sealed. See `operational/assignments/chiron-inventory/CHI-016-DRAIN-CLOSEOUT-2026-08-21.md`.

---

## ✅ Live by default: 92 · 🟡 Reachable (opt-in): 34 · Together: 126

**92 operational (default-live)**: all of Tier A (60, closed/calibrated) plus 32 of Tier B's 45
(B1 2, B2 6, B3 6, B4 8, B5 3, B7 4, B8 3 — every pack except B6, which is retired). Live, correctly
wired, validated through the full thinking-map → release-gate → pytest toolchain. No engineering
work needed to calibrate any of them — a `PC-*` recipe is the only thing standing between
"operational" and "actually tuned," and none have been tuned yet (every pack closed **held** —
reviewed and confirmed correct, not moved).

**34 accommodated (gated, opt-in)**: all of Tier C's C1–C5, real and tested, reachable the moment
`HESPERIA_TFP_FIELD_DYNAMICS=1` is set — but off by default, so they don't count as "operational"
in the same sense as the 92 (which are live with zero configuration). Use "126 total reachable
today" if the opt-in gate counts for your purposes; use "92 on by default" if it doesn't — both are
honest readings, just answering slightly different questions.

## ⛔ Retired — permanently, param by param, and why (18)

Retired means: not a bug to fix, not blocked-pending-engineering — genuinely no longer a
calibration target. Nothing here comes back without a new architecture decision reopening it.

| Params (18) | Retired because | Decided by |
|---|---|---|
| B6's 13 — `ultra_sparse_coverage_threshold`, `excessive_jump_threshold`, `transition_concentration_threshold`, `entropy_threshold`, `coverage_threshold`, `dominant_area_share_threshold`, `unique_areas_max`, `stability_high_threshold`, `curvature_threshold`/`severe_curvature_threshold`, `jump_rate_threshold`/`severe_jump_rate_threshold`, `low_stability_threshold` | `sphere/diagnostics/` (the module reading `diagnostic_rules.yaml`) had **zero live callers and zero tests, ever** — a single commit, never wired, never exercised. Tuning any of these 13 would change a number nothing reads. Layer-9 (`logic_rules.yaml`) is the real, live diagnostic system and was never this pack. | [CHI-006](CHI-006-diagnostic-thresholds-b6-unwired-finding.md) finding → [CHI-B16-03](../../../operational/assignments/reports/GENA-CHI-B16-CLOSEOUT-2026-08-21.md) (Gena) deprecated the module in code |
| C6's 5 — `alpha_H`, `beta_H`, `gamma_H`, `delta_H`, `dt` (`profiles_v1.json` `hex_field_reference`) | The nested key was never read by any code, anywhere — confirmed by name-grep across the whole repo, zero hits. Unlike B6, the surrounding *file* is live (its sibling keys feed C5) — only this one nested object was dead weight. | [CHI-013](CHI-013-tier-c-reachability-verification.md) finding → [CHI-014-02](../../../operational/assignments/chiron-inventory/SPEC-ETHAN-CHI-014-OPEN-FEASIBLE-2026-08-21.md) (Felix, `8d4e71d8`) deleted the key from the JSON |

## 🚫 Rejected — architecture options considered and turned down, and why

Distinct from retired *parameters*: these are specific **proposals** Grace/Ethan explicitly said no
to while deciding what to do with the findings above. Recording them so nobody re-proposes the
same thing without new evidence.

| Option rejected | For | Reason | Decided by |
|---|---|---|---|
| Wire `sphere/diagnostics/run_diagnostics()` into `/product/interpret` | B6 | Would create a second, divergent diagnostic system on the one product surface that matters most — same product-risk pattern Grace refused everywhere else this wave | Grace, [GRACE-TRIAGE-CHI-B1-B6-WIRING](../../../operational/assignments/reports/GRACE-TRIAGE-CHI-B1-B6-WIRING-2026-08-21.md) |
| "Document only" (leave B1's two hardcoded copies as-is, just note the disconnect) | B1 | Weak — leaves the actual bug (calibratable YAML doing nothing) unfixed and the real gate un-labeled | Grace, same triage — locked "wire" instead |
| Retire `activation_calibration.py` entirely (Copy A) | B1 | Rejected in favor of wiring it in — the module's `calibrate_thresholds_from_corpus()` becomes real once wired, not thrown away | Grace, same triage |
| Wire C1–C5 into `/product/interpret` **directly**, or without a named consumer | Tier C, all of C1/C2/C3/C5 | Invents product surface nobody asked for; "no silent interpret dump" stated as a hard refusal — **still true after CHI-015**: the operator named TFP as the consumer and Felix built a *gated, opt-in* envelope, not a default-interpret wire. This rejection is about the specific *unconsented, default-on* version of the move, not accommodation in general. | Ethan + Grace, [SPEC-ETHAN-CHI-013](../../../operational/assignments/reports/SPEC-ETHAN-CHI-013-TIER-C-WIRING-DESIGN-2026-08-21.md) / [GRACE-TRIAGE-CHI-013](../../../operational/assignments/reports/GRACE-TRIAGE-CHI-013-TIER-C-2026-08-21.md); superseded-in-part by [GRACE-TRIAGE-CHI-015](../../../operational/assignments/chiron-inventory/GRACE-TRIAGE-CHI-015-TFP-ACCOMMODATE-TIER-C-34-2026-08-21.md) once TFP was named |
| Retire the whole C1/C2/C3/C5 offline pack (option A3) | Tier C cluster A | "High regret if research still uses `run_e2e_all`" — rejected unless research owners explicitly agree; nobody has | Ethan, same SPEC |
| Emit HSPR as a runtime score into the live envelope (option B2) | C4 | Wrong type — HSPR is a meta-calibration fitness function for grid-searching other constants, not a per-request runtime metric; folding it into product output would misrepresent what it measures | Ethan, same SPEC |
| Numeric retune of any Tier B or Tier C constant this wave | All packs | Every finding this wave was architecture (wiring/dead-code), not a calibration question — tuning a number was never the fix for a disconnected pointer | Grace, both triage packets, stated as a hard refusal each time |

---

## What would move a number now

- **92 → higher**: only if a Tier B pack got mis-classified (re-audit) — nothing pending.
- **34 → 0 (accommodated → fully operational)**: only if the TFP gate defaults flip to on for a
  named product surface — a real product decision, not a Chiron move, and not requested.
- **34 → lower another way**: if a future CHI reachability pass finds part of the envelope isn't
  actually exercised the way this one claims — re-verify before trusting this snapshot past a few
  days old, same as always.
- **18 retired**: 13 B6 permanent + 5 C6 key hygiene; neither returns to tune targets.
- **4 stays 4**: permanent by design.

## Chiron's own accounting for this pass

Tier A/B closed. Tier C fully accommodated (C1–C5 gated via TFP, C6 retired). Tier D out of scope.
Verified the CHI-015 wave's code myself (11/11 pytest, `import hesperia.modules.tfp` clean,
existing `clinical_bridge` suite unaffected) before committing and pushing it — it was sitting
uncommitted in the shared workspace checkout when I found it. Next Chiron grind only if audit
finds drift in the 92 or 34, or a new Tier C-shaped extension gets added upstream.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | full-registry status snapshot, post CHI-B16 + CHI-013
SIGNED: Developer (Felix) | CHI-014-02 | 2026-08-21 | C6 hex_field_reference removed; inventory 92/34/18/4
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | added per-item retired reasons + rejected-options table, operator request
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | verified + committed CHI-015 (Hesperia `1215569`); inventory now 92 operational / 34 accommodated / 0 blocked / 18 retired / 4 sealed
