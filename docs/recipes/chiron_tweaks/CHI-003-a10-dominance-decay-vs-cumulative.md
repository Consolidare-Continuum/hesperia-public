# CHI-003 — A10-dominance investigation: real evidence toward "accumulation artifact," not settled theory

## 1. Task/goal

Close (with real evidence, not more flagging) the open item from `BACKLOG.md`'s Phase 4a note:
"A10 dominance across sessions ... Could be genuine ... could be a real bias in the area/family
rollup math. Flagged twice now, never actually root-caused." Ran a real, standalone diagnostic
against all 14 real TFP sessions comparing the production dominant-area metric against a proper
temporal-decay model. Result: real evidence toward artifact, not a settled conclusion — this is
a finding to ground a theory/design decision, not a fix to merge.

## 2. Method (two false starts corrected before the real comparison, kept here for the record)

**False start 1**: read `research/clinical_tfp/session_topology.py`'s per-segment `09_session_topology.json`
data as if it were the production "dominant area" figure. It isn't consumed anywhere as a final
answer — it's per-turn diagnostic detail.

**False start 2**: built a naive "cumulative" baseline (flat sum of per-segment `areas` across all
turns) and compared *that* against a Phase1Theta decay simulation. The Phase1Theta run was valid;
the baseline wasn't — it doesn't match what the pipeline actually reports as dominant
(`_maybe_speaker_aware()`'s `areas_top`, itself a *third*, whole-text-at-once computation, disagreed
with both).

**Real baseline, confirmed**: `02_session_tfp_stages.json` → `session_tfp_stages[0].areas_final` —
traced via `tools/tfp_calibration_audit.py`'s own `FINAL_AREA_DISTRIBUTION_COLLAPSED` check (the
exact mechanism BACKLOG.md's original "13/13, mass share 0.61–0.96" claim cites) back to
`hesperia/nlp/invariant_activation.py::build_invariant_activation()`'s `areas_final =
_softmax_area_vector(...)` — a **single softmax over the whole session's accumulated concept mass**,
computed once, no per-turn decay. Reran all 14 real sessions fresh (today's dict/corpus state):
**A10 dominant in 14/14**, mass share `0.445`–`0.963` (one genuine near-tie at `11-09-2023`,
`0.445` vs `A1`'s `0.428` — not hidden, reported as-is). This *confirms* the original finding was
real and reproducible, stronger than an earlier same-session mischeck suggested (which used the
wrong field and got 7/14).

**Decay comparison, real**: fed each session's real per-segment `areas` (12 turns,
`09_session_topology.json`) sequentially into `hesperia/extensions/dynamics/phase1.py::step_phase1()`
— the actual sealed Field Dynamics Phase1Theta step (`lambda_a=0.35` decay, `gamma_f=0.4`
injection gain, real icosahedral diffusion), unmodified, called standalone as a read-only
diagnostic (no pipeline file touched). TFP's 10-area vector padded into the required 12-slot shape
per `core/projection/area_math_grain.py`'s own documented grain=10 convention (indices 10–11 = 0,
sliced back to 10 before reading the result) — not invented, an existing sanctioned technique.

## 3. Result

| Session | `areas_final` dominant | share | Phase1Theta decay dominant | share | Agree |
|---|---|---|---|---|---|
| 02-03-2026 | A10 | 0.939 | A1 | 0.407 | No |
| 11-09-2023 | A10 | 0.445 | A1 | 0.560 | No |
| 14-12-2023 | A10 | 0.562 | A1 | 0.357 | No |
| 15-02-2024 | A10 | 0.641 | A1 | 0.294 | No |
| 15-12-2025 | A10 | 0.837 | A10 | 0.225 | Yes |
| 20-02-2025 | A10 | 0.657 | A6 | 0.321 | No |
| 20-10-2025 | A10 | 0.963 | A10 | 0.704 | Yes |
| 21-08-2025 | A10 | 0.729 | A10 | 0.246 | Yes |
| 22-08-2024 | A10 | 0.811 | A1 | 0.513 | No |
| 23-05-2024 | A10 | 0.755 | A1 | 0.470 | No |
| 24-02-2025 | A10 | 0.657 | A6 | 0.321 | No |
| 24-04-2025 | A10 | 0.612 | A1 | 0.399 | No |
| 26-12-2024 | A10 | 0.876 | A10 | 0.354 | Yes |
| 28-10-2024 | A10 | 0.873 | A10 | 0.269 | Yes |

**Agreement: 5/14 (36%)**. Where they disagree, decay's replacement is almost always A1, not a
scatter of different areas — a real pattern, not noise. The sessions where they *do* agree tend
to have the highest `areas_final` share (`0.729`–`0.963`, except `15-12-2025` at `0.837`) —
consistent with "when the cumulative signal is overwhelming, decay doesn't change the answer;
when it's more contested, decay does."

## 4. Interpretation — theory question, not an engineering verdict

This is evidence, not proof. Two honest readings, both consistent with the data:

- **Artifact reading**: `areas_final`'s no-decay whole-session softmax structurally favors whatever
  area accumulates the most raw activation regardless of *when* — an area discussed heavily early
  and never again looks identical to one discussed steadily throughout. A10 ("процесс лечения" /
  treatment-process) plausibly gets front-loaded discussion (intake, treatment-frame-setting) in
  many TFP sessions, then genuinely recedes — cumulative math can't see that, decay can.
- **Genuine-content reading**: TFP sessions may legitimately be treatment-process-centered
  *throughout*, and Phase1Theta's specific decay/injection constants (`lambda_a=0.35`, tuned for a
  different context — Field Dynamics was never calibrated against TFP data, confirmed zero
  references to it anywhere in the TFP pipeline) may simply be too aggressive, manufacturing A1
  dominance as its own artifact rather than revealing truth.

**This is exactly the kind of theory-grounding question Chiron's own spec routes through Colombo**
(CHROMA-2, TFP clinical theory) — not something to resolve by picking whichever math result is
more convenient. Does TFP theory (Clarkin/Yeomans/Kernberg) predict treatment-process content
should dominate a session's *overall* signature, or should it naturally recede once past the
opening phase? That answer should drive which computation (or a third, properly-TFP-calibrated
decay model) is the *right* one — not the reverse.

## 5. What this is NOT

- Not a claim that Phase1Theta's specific constants are correct for TFP — they were never tuned
  for it (§4 above).
- Not a recommendation to wire Field Dynamics into the TFP pipeline — that's real new integration
  work (`core/layers/`-adjacent), Felix/Gena territory, and premature before the theory question is
  answered.
- Not a claim that `areas_final` is wrong — cumulative-mass and decay-weighted-recency are both
  legitimate ways to define "the dominant theme," they just answer different questions.

## 6. Validation evidence

Standalone script, read-only, no pipeline/sealed-code file touched: `/tmp/a10_decay_v2.py`
(not committed — scratch diagnostic; the method is fully reproducible from this doc: real
`09_session_topology.json` segments → `step_phase1()` → compare against real
`02_session_tfp_stages.json.areas_final`). Ran against all 14 real sessions currently on disk, not
a subset. Every number in §3 is a live rerun against today's dict/corpus state, not carried over
from an earlier session's artifacts.

## 7. Rollback / follow-up

Nothing shipped, nothing to roll back. Follow-up, in order: (1) Colombo — does TFP theory predict
treatment-process content should dominate a session's whole-session signature, or recede after the
opening phase; (2) if decay is the right model, Felix/Gena would need to either calibrate Field
Dynamics constants against real TFP data first (not reuse untuned defaults) or build a
TFP-native decay computation from scratch — real work, not a toggle.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-20 | investigation, real evidence gathered, theory question handed to Colombo
