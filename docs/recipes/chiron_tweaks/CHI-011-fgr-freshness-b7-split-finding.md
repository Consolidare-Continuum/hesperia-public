# CHI-011 — FGR/Freshness calibration (B7): 2 of 4 live via a different file than documented, 2 of 4 currently unreachable from any live route

## 1. Task/goal

Seventh Tier B pack — the registry's own flagged exception: "the only group whose 'output' is LLM
narration permission, not a report number... different validation shape." Review the 4 registry
candidates (`DOMINANT_SHARE_HIGH`, `ENTROPY_DROP_SIGNIFICANT`, `STABILITY_CURRENT_THRESHOLD`,
`STABILITY_STALE_THRESHOLD`, `parameter_synergies.md` §4). Full disclosure up front: this pack
directly maps Hesperia's own structural output onto the same `fpf_thinking_map` primitives
(`FGR`, `Freshness`, `EvidencePrimitive`) that Chiron's own §3 gate uses every session via
`cursor-fpf-test-mcp` — a genuine, unplanned overlap worth noting, not just documenting.

## 2. Where the four candidates actually live — split finding, traced precisely

Two files each define calibration constants for structural evidence trust, and they are **not**
the same reachability story per parameter:

| Parameter | Where defined | Consumer | Live? |
|---|---|---|---|
| `DOMINANT_SHARE_HIGH=0.35` | `sphere/interpretation/state_classifier.py` (own copy) | `classify_structural_state()` | **Live** — called from `sphere/interpretation/engine.py::compute_interpretation_metrics()`, called from `sphere/pipeline/pipeline_runner.py` (Layer-10, the same sealed pipeline CHI-006/CHI-007 already traced into `/product/tfp` et al.) |
| `DOMINANT_SHARE_HIGH=0.35` | `sphere/fpf_bridge/constants.py` (separate hardcoded copy, comment: "matching state_classifier.py" — **not imported**, independently maintained) | `evidence_mapper.py::_rule_fgr()` | Not reachable — see below |
| `ENTROPY_DROP_SIGNIFICANT=0.15` | `state_classifier.py` (own copy) | `classify_entropy_state()` | **Live** — same chain as above |
| `ENTROPY_DROP_SIGNIFICANT=0.15` | `fpf_bridge/constants.py` (separate copy) | `evidence_mapper.py::_rule_fgr()` | Not reachable — see below |
| `STABILITY_CURRENT_THRESHOLD=0.7` | `fpf_bridge/constants.py` only — **no counterpart anywhere else** | `evidence_mapper.py::map_stability_to_freshness()` | Not reachable — see below |
| `STABILITY_STALE_THRESHOLD=0.3` | `fpf_bridge/constants.py` only — **no counterpart anywhere else** | `evidence_mapper.py::map_stability_to_freshness()` | Not reachable — see below |

**Reachability trace for `evidence_mapper.py`'s consumers** (grepped, not assumed): its only real
callers are `sphere/fpf_bridge/bridge.py` and `binding_builder.py`. Their only callers in turn:
`runtime/shipping/llm_integration.py` and `runtime/agentic_bridge/{get_state,attempt_transition}.py`.
Checked every real live-route file for a reference to any of these: `runtime/api/main.py`,
`runtime/shipping/api_main.py` (both `mode="deterministic"` and `mode="llm"` branches of
`POST /product/interpret`), `sphere/pipeline/pipeline_runner.py`, `hesperia/product/service.py` —
**zero references to `fpf_bridge`, `llm_integration`, or `bridge_to_llm_prompt` in any of them.**

The `mode="llm"` branch in `product_interpret_service.py` (line 157) — the one place a live route
does branch on an LLM mode — uses `sphere.router.llm_interpret::interpret_router_envelope`, a
**different module entirely**, not `fpf_bridge`. `runtime/agentic_bridge/*` is separately, already
correctly documented as gated: `EXTENSION_STATUS.yaml` marks it `status: experimental,
product_surface: none`, "Flag-gated off; ratification pending" — matches the prior session's
`HES-PROD-A03` security hold (Daniel, 2026-08-10). That part of the picture was already accurate;
this review's finding is specifically that `fpf_bridge`'s own status line overstates its reach.

## 3. The documentation claim, checked precisely

`EXTENSION_STATUS.yaml`: `fpf_bridge: status: canonical_extension, product_surface: internal...
"Used inside mode='llm' product_interpret path; not a public plugin contract itself."` The
`product_surface: internal` classification is honest (doesn't claim public/shipped status) — the
specific factual claim "used inside `mode='llm' product_interpret` path" does not hold up under
direct trace of that exact branch (§2). `hesperia-wiki` repeats the same "running in production
path" framing for all 4 params, including `STABILITY_CURRENT_THRESHOLD`/`STABILITY_STALE_THRESHOLD`
which have no live counterpart anywhere. Same category of finding as CHI-006 (wiki/doc claims
outrunning the actual call graph), narrower in scope: 2 of 4 params here are genuinely live (just
via a different file/function than the one the docs point to), and the module itself is real,
substantially tested code with a legitimate internal purpose — not an accidental zero-coverage
orphan like B6.

**Secondary, smaller finding**: `fpf_bridge/constants.py`'s comment "matching state_classifier.py"
for its `DOMINANT_SHARE_HIGH`/`ENTROPY_DROP_SIGNIFICANT` copies is currently true (both files hold
`0.35`/`0.15`) but structurally fragile — two independently-maintained hardcoded copies, kept in
sync only by comment discipline, not a shared import. Not a live bug today; a drift risk if either
file is edited without the other.

## 4. Validation evidence

- Reachability trace (§2) — direct grep + read across every real orchestrator, not inference.
- `tests/test_fpf_bridge.py` + `tests/test_llm_integration.py`: **55 passed, 1 failed** —
  `TestProviderErrors::test_openai_without_key_raises` fails both in the full run and in isolation;
  confirmed unrelated to the 4 calibration params (it asserts `RuntimeError` on a missing
  `OPENAI_API_KEY` inside `interpret_prompt_state`/`LlmInterpretConfig`, a provider-validation path
  that doesn't touch `DOMINANT_SHARE_HIGH`/`ENTROPY_DROP_SIGNIFICANT`/`STABILITY_*`). Confirmed
  environment has no `OPENAI_API_KEY` set (`printenv` empty) — pre-existing test/code drift, not
  environmental pollution, and definitionally pre-existing since no code was touched this session.
  The substantial pass rate (55/56) confirms `fpf_bridge` is real, deliberately-built, tested
  code — the opposite character from B6's zero-test orphan.
- §3 thinking-map gate (`cursor-fpf-test-mcp`, `scope="core"`): three evidence items (the
  live/unreachable split, the unreachability trace across every real route, the test-coverage
  confirmation), `attempt_transition()` → **`OutcomeKind.CONTINUE`**, zero validation errors, zero
  missing evidence.

## 5. Verdict: hold, correct the documentation, no code change

No parameter value needs to move — `DOMINANT_SHARE_HIGH=0.35`/`ENTROPY_DROP_SIGNIFICANT=0.15` are
correctly calibrated where they're actually live (`state_classifier.py`), and
`STABILITY_CURRENT_THRESHOLD=0.7`/`STABILITY_STALE_THRESHOLD=0.3` are reasonable values for a
feature (`fpf_bridge`'s LLM-facing evidence trust layer) that is real, tested, and deliberately
staged as `product_surface: internal` — not a mistake to fix, a genuinely-not-yet-wired-to-a-live-route
internal layer, same shape as `agentic_bridge`'s already-acknowledged hold. Nothing here rises to
CHI-006's "propose a wiring decision" bar — `fpf_bridge` isn't claiming to be product-facing the
way B6's diagnostics module implicitly was via the Tier B blanket claim; it's honestly labeled
`internal`, just with one overstated specific claim about *which* path uses it.

## 6. Config

No change. Both files' constants remain as found.

## 7. Invocation (for reference)

`state_classifier.py`'s live copies are exercised automatically whenever `sphere/pipeline/pipeline_runner.py::run_pipeline()`
runs (same 4-orchestrator chain as CHI-008/009/010). `fpf_bridge`'s `bridge_to_llm_prompt()` /
`map_stability_to_freshness()` are currently only invokable directly (as the test suite does) or
via the flag-gated `agentic_bridge` — not through any live HTTP route today.

## 8. Expected output shape (unchanged)

`state_classifier.py`'s output (`structural_state`, `entropy_state`, etc.) feeds Layer-10's
interpretation metrics as before. `fpf_bridge`'s `EvidencePrimitive`/`Freshness` output shape is
unchanged — still real, still tested, still not yet reachable from a live request.

## 9. Rollback / doc corrections made this session

No rollback needed — nothing changed. `CANDIDATE-REGISTRY.md`'s B7 row updated to note the
live/unreachable split precisely instead of a blanket "live" status. **Not corrected directly**
(Chiron reports, per spec §8a for wiki content, and doesn't unilaterally rewrite
`EXTENSION_STATUS.yaml`'s ownership either): flagging both the wiki's 4 "running in production
path" claims and `EXTENSION_STATUS.yaml`'s specific `mode='llm'` claim to `inbox.md` for
Felix/Colombo awareness. The `fpf_bridge/constants.py` vs `state_classifier.py` duplicate-copy
drift risk (§3) is a real, small, low-urgency cleanup candidate (import from one instead of
maintaining two) — flagged, not actioned, since it's a code-structure change outside a calibration
review's scope.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | B7 reviewed via full thinking-map/pytest toolchain — split finding: 2 of 4 params live via a different file than documented, 2 of 4 real/tested but not yet reachable from any live route; no code change, doc corrections flagged
