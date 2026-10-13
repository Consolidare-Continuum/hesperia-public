# CHI-010 — Core Math governance penalties (B4): live, correctly documented, held at defaults

## 1. Task/goal

Sixth Tier B pack (grind order: B8 → B6 blocked → B2 → B5 → B3 done → **B4** next, "bigger
governance set"). Review the 8 registry-named candidates (`k_amb`, `delta_gap`, `tau_core`,
`k_thin`, `k_disp`, `k_guard`, `k_shadow`, `max_shadow_hops`, all `core/math/core_math.py
DEFAULT_CONFIG`) — same file as B3/B5, same reachability chain, so this review leans on the
already-confirmed live-path trace rather than re-deriving it, and focuses effort on the
parameter-specific formulas and documentation cross-check.

## 2. Where the eight candidates live and what consumes them

Five penalty functions, each computing one additive term of `metric_governance`:

| Params | Function | Formula |
|---|---|---|
| `k_amb`, `delta_gap` | `ambiguity_penalty()`, line 293 | `gap=(e1-e2)/(e1+eps)`; `P_amb=k_amb·(1-gap)²`; `degraded = gap < delta_gap` |
| `tau_core`, `k_thin` | `thin_core_penalty()`, line 313 | `CoreShare=sumS/(sumS+sumL+eps)`; `P_thin=k_thin·(1-CoreShare)`; `degraded = CoreShare < tau_core` |
| `k_disp` | `dispersion_penalty()`, line 329 | `P_disp=k_disp·H_norm` (normalized Shannon entropy of `E_end`) |
| `k_guard` | `guard_penalty()`, line 348 | `P_guard=clamp(k_guard·(sigma_fail+gamma_violation+theta_reject), 0, 1)` |
| `k_shadow`, `max_shadow_hops` | `P_shadow_value()`, line 400 | `P_shadow=clamp(k_shadow·(shadow_hops/max_shadow_hops), 0, 1)` |

All five feed `metric_governance()` (line 359): `clamp(1 − (P_amb+P_thin+P_shadow+P_disp+P_guard),
0, 1)` — one health number. Same reachability chain B3/CHI-008/CHI-009 already confirmed:
`core_math.py`'s own `analyze()`/`_analyze_raw()` call these directly; `runtime/pipeline/analyze.py`
imports `core_math.analyze`; called from `run_tfp_file_pipeline.py`, `run_e2e_all.py`,
`run_e2e_sentence.py`, `research/clinical_tfp/product_analyze.py`. Not re-traced from zero — same
entrypoint as the two prior packs this session.

## 3. Documentation cross-check — no gap found, and the wiki confirms it independently

`hesperia-wiki` queried for all 8 params: `P_amb`, `P_thin`, `P_disp`, `P_guard`, `P_shadow`, and
the `metric_governance` hub itself all return `LIVE_FULL`, formulas and values matching source
exactly (`k_amb=0.35`, `delta_gap=0.08`, `tau_core=0.25`, `k_thin=0.30`, `k_disp=0.25`,
`k_guard=0.30`, `k_shadow=0.40`, `max_shadow_hops=2`).

Notable, worth recording precisely: the `energy_conservation_tolerance` wiki page carries its own
note dated 2026-08-04, from a prior full `parameter_catalog.md`-vs-wiki cross-check pass: *"every
other §3/§4 constant (k_amb, tau_core, k_thin, k_disp, k_guard, k_shadow, delta_gap,
max_shadow_hops, w_decay/w_guard_obs/w_shadow_obs, severe_curvature_threshold,
severe_jump_rate_threshold) turned out already covered... `energy_conservation_tolerance` was the
only genuine gap found."* That's independent, dated confirmation — from a different pass, before
this session — that B4's 8 params specifically were already checked and found clean. This review
re-confirmed rather than newly discovered that cleanliness.

`parameter_synergies.md` has no entry naming any B4 param (grepped — zero hits), consistent with
the registry's own framing ("tuned relative to each other, not absolute" is a design note about
how the five penalties compose additively, not a formal cross-file constraint like B2/B5's
sum-to-1.0).

## 4. Validation evidence

- `python core/math/core_math.py test`: **7 passed, 0 failed** (re-run this session, same as
  CHI-009 — nothing changed between packs, cited fresh rather than assumed stale).
- Demo run: `governance: 0.335`, and critically the `degraded` dict —
  `{'ambiguity': False, 'thin_core': False, 'no_centroid': False, 'shadow_overuse': False}` — all
  four degradation flags computed and correctly `False` on non-degenerate synthetic input,
  confirming the penalty system evaluates and doesn't silently no-op.
- Reused from CHI-008/CHI-009 (same session, same code path): the broader `analyze()` pytest suite
  (`test_e2e_flows`, `test_invariant`, `test_attribution`, `test_adversarial`, `test_guard_pipeline`,
  `test_engine_analyze_contract`) already confirmed green.
- §3 thinking-map gate (`cursor-fpf-test-mcp`, `scope="core"`): three evidence items (live-fire
  trace, doc cross-check including the 2026-08-04 independent confirmation, self-test/demo
  baseline), `attempt_transition()` → **`OutcomeKind.CONTINUE`**, zero validation errors, zero
  missing evidence.

## 5. Verdict: hold at current defaults

No evidence or gap surfaced to justify moving any of the 8 values. The penalty weights are
internally consistent by design (each independently CI-testable per the wiki's own framing, not
constrained to sum to anything) and the wiki's dated cross-check plus this session's fresh trace
both confirm the documentation is accurate. Clean result, same character as B3/CHI-009.

## 6. Config

No change. `DEFAULT_CONFIG` values remain as found.

## 7. Invocation (for reference)

Same as CHI-008/CHI-009 §7 — `python core/math/core_math.py test` / `python core/math/core_math.py`
(demo) exercise this pack directly; the same 4 real orchestrators exercise it against live/
TFP-adjacent input on the default (English) analyze profile.

## 8. Expected output shape (unchanged)

`metric_governance` in `[0,1]`, plus the four boolean `degraded` flags
(`ambiguity`/`thin_core`/`no_centroid`/`shadow_overuse`) in `analyze()`'s output — unchanged by
this review.

## 9. Rollback / registry update

No rollback needed — nothing changed. `CANDIDATE-REGISTRY.md`'s B4 row marked reviewed/held.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | B4 reviewed via full thinking-map/self-test/pytest toolchain, verdict: hold at current defaults — clean result, independently confirmed by both this session's trace and a prior (2026-08-04) wiki cross-check
