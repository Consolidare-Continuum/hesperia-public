# CHI-009 — Core Math fusion/traversal (B3): live, correctly documented, held at defaults

## 1. Task/goal

Fifth Tier B pack (grind order: B8 done → B6 blocked → B2 done → B5 done → **B3** next, "bigger
physics set"). Review the 6 registry-named candidates (`alpha`, `eta`, `K_max`, `lambda`, `decay`,
`E_cap`, `core/math/core_math.py DEFAULT_CONFIG`) — the same file B5 already traced into 4 real
orchestrators, so reachability is largely inherited from that trace rather than re-derived from
scratch. Unlike B6/B7/B8, this pass found no gap between documentation and code — recorded
precisely as a clean result, not stretched into a finding that isn't there.

## 2. Where the six candidates live and what consumes them

`core/math/core_math.py::DEFAULT_CONFIG` (lines 41-46): `alpha=0.65`, `E_cap=1.0`, `K_max=5`,
`eta=0.02`, `lambda=0.55`, `decay=0.04`. Feed the fusion/traversal physics directly:

| Parameter | Formula | Function |
|---|---|---|
| `alpha`, `E_cap` | `E0[i] = clamp(α·S'[i] + (1−α)·L'[i], 0, E_cap)` | `fusion()`, line 202 |
| `eta`, `K_max` | `active = [i where E0[i] > eta]`, top-`K_max` by `E0` desc | `centroid_indices()`, line 223 |
| `lambda`, `decay`, `E_cap` | `D = (1−λ)E + λ(EW)`, `E_next = clamp(D·(1−decay), 0, E_cap)` | `base_step()`, line 240, iterated `T_steps=8` times |

Same reachability chain B5/CHI-008 already confirmed: `core_math.py`'s own `analyze()`/
`_analyze_raw()` call `fusion()`/`centroid_indices()`/`base_step()` directly; `runtime/pipeline/analyze.py`
imports `core_math.analyze`; called from `run_tfp_file_pipeline.py`, `run_e2e_all.py`,
`run_e2e_sentence.py`, `research/clinical_tfp/product_analyze.py` — not re-traced from zero this
pass, inherited from CHI-008's confirmed chain since it's the identical entrypoint.

## 3. Documentation cross-check — no gap found

`parameter_catalog.md` §3 and `hesperia-wiki` both checked against source directly, not assumed:

- `alpha (fusion weight)`, `eta (centroid threshold)`, `E_cap`, `lambda (lazy step)`, `decay` all
  return `LIVE_FULL` from the wiki with formulas and values matching source exactly (`0.65`/
  `0.02`/`1.0`/`0.55`/`0.04`) — no discrepancy like CHI-006's dead-code claim or CHI-007/CHI-008's
  overstated "CI-enforced"/"live path" wording.
- `K_max` is documented correctly in `parameter_catalog.md` §3 (caps centroid count) and confirmed
  live in `centroid_indices()`; no dedicated wiki page surfaced in this query but nothing
  contradicts the catalog either.
- `parameter_synergies.md` has no entry for B3 (grepped — zero hits for `alpha`/`K_max`/`E_cap`/
  traversal `lambda` naming a must-move-together set), matching the registry's own framing of B3
  as "one physics set" described narratively rather than as a formal cross-file synergy like B2/B5.
- The wiki's own note on `lambda (lazy step)` is worth restating precisely: "hand-set weights, not
  learned... 'Markov-like', never 'fitted Markov chain / HMM'" — a terminology discipline point
  already correctly enforced in the doc, not something this pass needed to correct.

## 4. Validation evidence

- `core_math.py`'s own self-test (`python core/math/core_math.py test`): **7 passed, 0 failed** —
  directly exercises `alpha` (fusion L-only/S-only sum checks), `lambda`/`decay`/`E_cap` (I-R2
  conservation check on `base_step`), the F5 zero-input guard, I-R3 shadow non-creation, plus
  `validate_config` (already covered under CHI-008 for the `w_*` weights, re-confirmed here as
  part of the same run).
- Demo run (`python core/math/core_math.py`): real computed values —
  `governance: 0.335`, `loopability: 0.601`, `tension_energy: 1.39e-09`, `obstacle_score: 0.139`,
  `conservation_ok (I-R2): True`, `shadow_non_creation_ok (I-R3): True` — the fusion/traversal
  chain producing sane, in-range output end to end on real (synthetic-demo) input.
- `tests/energy_invariants_stress.py` + `tests/architecture/test_no_math_in_sphere.py`: **2
  passed** — the file referencing `centroid_indices`/`K_max`/`eta` directly.
- Reused from CHI-008 (same session, same code path, not re-run): `test_e2e_flows.py`,
  `test_invariant.py`, `test_attribution.py`, `test_adversarial.py`, `test_guard_pipeline.py`,
  `test_engine_analyze_contract.py` — all green, exercising the full `analyze()` chain including
  fusion/centroid/traversal.
- §3 thinking-map gate (`cursor-fpf-test-mcp`, `scope="core"`): three evidence items (live-fire
  trace, doc cross-check, test baseline), `attempt_transition()` → **`OutcomeKind.CONTINUE`**,
  zero validation errors, zero missing evidence.

## 5. Verdict: hold at current defaults

No real-session evidence or documentation gap surfaced to justify moving `alpha=0.65`,
`eta=0.02`, `K_max=5`, `lambda=0.55`, `decay=0.04`, or `E_cap=1.0`. The compounding nature of this
pack (`base_step` iterated `T_steps=8` times) means any change here has amplified downstream
effect — appropriately, the registry already scheduled B3 after the smaller/more isolated packs
(B8, B2, B5) rather than first, and this review found no reason to disturb that caution with an
unjustified tune. Clean result: live, correctly documented, tested, held.

## 6. Config

No change. `DEFAULT_CONFIG` values remain as found.

## 7. Invocation (for reference)

Same as CHI-008 §7 — `python core/math/core_math.py test` / `python core/math/core_math.py`
(demo) exercise this pack's math directly against `DEFAULT_CONFIG`; the same 4 real orchestrators
(§2) exercise it against live/TFP-adjacent input in the default (non-TFP) analyze profile,
matching CHI-008's already-documented English-lexicon scope boundary.

## 8. Expected output shape (unchanged)

`E0` (fused energy vector), `centroid_indices` (top-`K_max` active sides), `E_next` per traversal
step (bounded `[0, E_cap]`), feeding `governance`/`loopability`/`tension_energy`/`obstacle_score`
in the final `analyze()` output — unchanged by this review.

## 9. Rollback / registry update

No rollback needed — nothing changed. `CANDIDATE-REGISTRY.md`'s B3 row marked reviewed/held.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | B3 reviewed via full thinking-map/self-test/pytest toolchain, verdict: hold at current defaults — clean result, no documentation gap found, unlike the three prior packs this session
