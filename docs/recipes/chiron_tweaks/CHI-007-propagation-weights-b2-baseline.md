# CHI-007 — Propagation weights (B2): live, held at defaults; documented synergy spans two lanes that never co-occur

## 1. Task/goal

Third Tier B pack (grind order: B8 done → B6 blocked → **B2** next, "documented synergy, clear
pairing"). Review the 5 registry-named candidates (`center_to_inner`, `inner_to_middle`/
`middle_to_inner`, `middle_to_outer`/`outer_to_middle`, `bridge_weight`, `decay_factor`) plus a
6th, uncatalogued key found while tracing the module (`concept_to_family_multiplier`), and
specifically re-check `parameter_synergies.md` §2's claim that `bridge_weight` and shadow
correction's entropy cap are "calibrated as a pair" — B6 taught this session not to take a
documented live-path or synergy claim at face value without a direct call-graph trace.

## 2. Where the six candidates live and what actually consumes them

`assets/specs/canon/propagation_weights.yaml` → `sphere/topology/propagation_weights_loader.py::load_propagation_weights()`
returns all six keys, but only two of the six are read by any downstream consumer:

| Parameter | Value | Consumed by | Status |
|---|---|---|---|
| `center_to_inner` | 0.25 | `get_within_area_spread()` → `activation_propagation.py::propagate_within_area()` | Live |
| `inner_to_middle` / `middle_to_inner` | 0.18 | same | Live |
| `middle_to_outer` / `outer_to_middle` | 0.12 | same | Live |
| `bridge_weight` | 0.22 | `get_bridge_weight()` → `activation_propagation.py::propagate_across_bridges()` | Live |
| `decay_factor` | 1.0 | loaded, never read by any `get_*` accessor | **No-op** — already honestly disclosed in `parameter_catalog.md` §2 ("currently a no-op") |
| `concept_to_family_multiplier` | 1.0 | loaded, never read by any `get_*` accessor | **No-op, undocumented** — absent from `parameter_catalog.md`, `CANDIDATE-REGISTRY.md`'s B2 row, the wiki, and `Coverage-Ledger.md`'s known-gaps list. Confirmed via `hesperia-wiki` query (no record) before flagging, not assumed. |

## 3. Reachability — confirmed live, unlike B6

`propagate_activation()` is called from `hesperia/nlp/session_parser.py::analyze_session()`
(line 419) and `hesperia/nlp/invariant_activation.py` (line 493). `session_parser.analyze_session`
is in turn called by `runtime/pipeline/run_tfp_file_pipeline.py` (the real backend behind
`tools/gena_tfp_bundle_run.py` and the TFP analyze lane, `hesperia-analyze-tfp.service:18881`) and
`runtime/pipeline/run_e2e_all.py`. Confirmed firing on a real session, not just reachable in
principle: re-inspected CHI-005's `outputs/tfp/runs/chi005_b8_baseline/20_main_engine_full_context.json`
(the real `--with-triz --with-topology` run against `tests/fixtures/tfp/input.txt`) —
`sessions[0].activation.propagation_trace = ["within_area:A2", "within_area:A3",
"within_area:A4", "within_area:A10", "across_bridges"]`, both intra-area spread *and* the bridge
path fired, 231 families carry nonzero post-propagation activation.

**Nuance worth recording**: the registry's Tier B header says these are "on the real
`/product/interpret` output path." Precisely: `propagate_activation` is on the **TFP analyze
lane** (`run_tfp_file_pipeline.py` / `/hesperia/analyze` with `profile=tfp`), not the literal
`POST /product/interpret` route (`runtime/services/product_interpret_service.py`, which — per
CHI-006's trace — uses a separate `sphere.router.pre_llm_compiler` path with zero reference to
`session_parser`/`activation_propagation` at all). Same imprecision CHI-006 caught for B6, but
here the parameter genuinely is live on a real, tested, production systemd service — just not
literally that one named route. Worth a registry wording pass across all of Tier B at some point,
not urgent enough to block this pack's own verdict.

## 4. The documented synergy — real claim, checked against the actual call graph

`parameter_synergies.md` §2: "`bridge_weight` (0.22) sits *between* the innermost zone weight
(0.25) and the next ring out (0.18)... Combined with shadow correction's entropy cap
(`corners/shadow_correction.md`)... Turning bridge weight up without separately re-validating the
shadow correction bound would silently change how much cross-area 'spillover' the system
tolerates... the two parameters are calibrated as a pair, not independently, even though they
live in different YAML files and different modules."

Traced whether that pairing is a same-request, enforceable interaction today, not assumed from
the prose:

- Shadow correction lives in `sphere/shadow/engine.py`, consumed by
  `sphere/pipeline/pipeline_runner.py` (the sealed Layer 1-10 pipeline backing `/product/tfp`,
  `/product/fingerprint`, `/product/llm-audit` via `hesperia/product/service.py`).
- `bridge_weight` lives in `propagation_weights.yaml`, consumed only via
  `session_parser.analyze_session` (the TFP batch/analyze lane).
- Checked all three real orchestrators that could plausibly run both in one request:
  `runtime/pipeline/run_tfp_file_pipeline.py` (zero references to "shadow" anywhere),
  `sphere/pipeline/pipeline_runner.py` (zero references to `session_parser`/
  `activation_propagation`/`propagate_activation`), `runtime/pipeline/run_e2e_all.py` (calls
  `session_parser`/`propagate_activation` in several branches, zero references to "shadow"
  anywhere in the file). **No code path runs both `bridge_weight`'s propagation and shadow
  correction's entropy cap within the same request.**

**This doesn't mean the synergy claim is wrong as a design-time consideration** — the reasoning
("higher bridge weight → more cross-area spillover → more entropy for something to cap") is sound
physics, and if these two systems are ever unified into one request path, the pairing would become
operationally real and the doc's warning would matter immediately. Today, precisely: it's a
*theoretical* coupling between two live-but-separate-lane parameters, not a same-request
enforceable one. Recording this precisely rather than either dismissing the doc or overstating an
operational risk that can't currently manifest.

## 5. Validation evidence

- Live-reachability trace (§3) — real bundle inspection, not inference.
- `tests/topology/test_activation_propagation.py` + `tests/propagation/` (3 files) +
  `tests/triz/test_propagation_topology.py` + `tests/layers/test_propagation_layer.py`: **34
  passed**, 0 failed — genuine, existing coverage (unlike B6's zero).
- §3 thinking-map gate (`cursor-fpf-test-mcp`, `scope="core"`): three evidence items (live-fire
  confirmation, dead-key trace, synergy-lane-separation trace), `attempt_transition()` →
  **`OutcomeKind.CONTINUE`**, zero validation errors, zero missing evidence.
- Wiki cross-check: `bridge_weight`, `center_to_inner`, `inner_to_middle`/`middle_to_inner` all
  `LIVE_FULL`; `decay_factor (propagation)` correctly `PARTIAL` ("reserved slot, not yet
  load-bearing beyond identity") — wiki matches the code trace exactly here, unlike B6's
  inaccurate claims. `concept_to_family_multiplier` has no wiki page at all (confirmed, not
  assumed missing).

## 6. Verdict: hold at current defaults

No real-session evidence surfaced to justify moving `center_to_inner=0.25`, `inner_to_middle`/
`middle_to_inner=0.18`, `middle_to_outer`/`outer_to_middle=0.12`, or `bridge_weight=0.22` off their
current values — the ladder shape (strongest at center, weakest at periphery, bridge weight
deliberately close to the strongest in-area edge) is a coherent, already-reasoned design, and this
pass found no corpus evidence pointing at a different ratio. `decay_factor` and
`concept_to_family_multiplier` stay at their no-op identity values (`1.0`) — nothing to tune in a
parameter nothing reads.

## 7. Config

No change. All six YAML values remain as found.

## 8. Invocation (unchanged, for reference)

`run_tfp_file_pipeline.py` / `tools/gena_tfp_bundle_run.py` (TFP analyze lane) call
`session_parser.analyze_session()` → `activation_propagation.propagate_activation()` implicitly;
no env var or flag needed beyond the existing TFP profile setup (`HESPERIA_ANALYZE_PROFILE=tfp`
or direct batch-tool invocation, same as CHI-005/§5).

## 9. Rollback / doc corrections made this session

No code rollback needed — nothing changed. `CANDIDATE-REGISTRY.md`'s B2 row updated: candidate
count 5→6 (`concept_to_family_multiplier` added, flagged no-op alongside `decay_factor`), status
set to reviewed/held with a pointer to this file and a short note on the synergy-lane-separation
finding. `parameter_synergies.md` §2 not edited directly (Chiron may propose, not silently rewrite
an existing foundational doc's claim) — flagging the lane-separation nuance in `inbox.md` for
Felix/Gena/Colombo awareness instead.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | B2 reviewed via full thinking-map/pytest toolchain + real-session reachability check, verdict: hold at current defaults; documented synergy confirmed theoretically sound but not same-request enforceable today; one undocumented no-op key found
