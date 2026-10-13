# CHI-012 — Activation floor (B1): the calibratable YAML is disconnected from the real live gate

## 1. Task/goal

Eighth and final Tier B pack — deliberately saved for last per the registry's own instruction:
"Foundational — every downstream ratio's denominator depends on these. Highest blast radius in
Tier B; grind last, most carefully." Review `activation_threshold=0.01` and
`area_active_threshold=0.05` (`assets/specs/canon/activation_calibration.yaml`). Given the stakes
this pack itself flagged, traced the full call graph before forming any opinion — same discipline
that caught CHI-006, applied with extra care here because this is explicitly the pack where a
wrong assumption would matter most.

**Finding, stated plainly up front**: the YAML file — the thing `CANDIDATE-REGISTRY.md` and
`parameter_catalog.md` §1 name as the source of these two "foundational, every-ratio's-denominator"
values — is **not connected to the real live activation gate**. A separate, independently
maintained copy in `hesperia/engine/kme/clinical_bridge.py` does the actual work. The two
currently hold identical values (`0.01`/`0.05` in both places), so there is no live drift today —
but editing the calibratable YAML, as its own comment instructs ("Tune after validation on 20–50
TFP transcripts"), would currently change nothing about real output.

## 2. Two independent copies, traced precisely

**Copy A — the registry's named source, unwired:**

`assets/specs/canon/activation_calibration.yaml` → `hesperia/engine/calibration/activation_calibration.py`:
`DEFAULT_ACTIVATION_THRESHOLD=0.01`, `DEFAULT_AREA_ACTIVE_THRESHOLD=0.05`, loaded by
`load_calibration_config()`, read via `get_activation_threshold()`/`get_area_active_threshold()`,
with a real, unused `calibrate_thresholds_from_corpus()` function meant to fit these from real
data. **Grepped every `.py` file in the repository for all three function names** — the only hits
are the module's own file and `hesperia/engine/calibration/__init__.py`'s re-export. Zero real
callers anywhere. `git log --oneline -- hesperia/engine/calibration/activation_calibration.py`
shows exactly one commit (`4bb8a5c7`, a large "TFP testing stack" commit that added many modules
at once) — created once, never modified, never wired, and no test file exists for it either
(`test_activation_calibration*.py` — zero matches).

**Copy B — the real live gate, undocumented as such:**

`hesperia/engine/kme/clinical_bridge.py` lines 207/210 define its own module-level constants:
`ACTIVATION_THRESHOLD = 0.01`, `AREA_ACTIVE_THRESHOLD = 0.05` — **not imported from Copy A**,
independently hardcoded. Used at **17 real call sites** gating concept, family, and area node/edge
construction: `build_concept_nodes()`, `build_family_nodes()`, `build_area_nodes()`,
area-adjacency edge construction, and several coactivation-edge filters — genuinely the mechanism
that decides what counts as "active" throughout KME graph building, matching the catalog's own
description of what this pack is supposed to control. `clinical_bridge.py` is confirmed reachable
(same trace already established across CHI-002/CHI-005/CHI-007/CHI-008 this session):
`run_session_kme_pipeline()` is called from `runtime/pipeline/run_tfp_file_pipeline.py` and
`runtime/pipeline/run_e2e_all.py` — the real TFP analyze lane. `tests/domain/test_clinical_bridge.py`
+ `tests/engine/kme/test_clinical_bridge.py`: **13 passed, 0 failed**, exercising this exact
threshold-gated logic.

**The two copies are not linked by any code** — no shared import, no runtime override path, no
test asserting they agree. They currently match by manual coincidence (or by whoever wrote
Copy B copying Copy A's values at the time, then neither being touched since — the single-commit
history of Copy A is consistent with this).

## 3. Documentation cross-check — imprecise on this pack specifically

`parameter_catalog.md` §1 describes `activation_threshold`/`area_active_threshold` accurately in
*effect* ("directly determines... the denominator of nearly every downstream ratio") but names
only `assets/specs/canon/activation_calibration.yaml` as the source — not clinical_bridge.py, the
actual live mechanism. `hesperia-wiki` attributes both params to a generic **"diagnostics config"**
module (neither Copy A's YAML path nor Copy B's `clinical_bridge.py` specifically), and both wiki
pages have empty `produced_from`/`needed_by` fields — noticeably thinner than the well-cited
entries this session found clean for B2–B5/B8 (compare CHI-007/CHI-009/CHI-010's wiki citations,
which name exact consuming functions). The thinness itself is a signal: this is the one pack where
the wiki's own research was incomplete, not just imprecise in wording.

This is a different character of finding than CHI-006 (a fully orphaned module, zero live path
anywhere) — here, the *values* are genuinely live and load-bearing, just via a path the
authoritative docs don't name. Closer to CHI-011's split finding (B7), but with higher stakes:
CHI-011's split params fed an internal, not-yet-product-facing LLM bridge; this pack's real values
gate the KME graph construction the catalog itself calls foundational.

## 4. Validation evidence

- Full call-graph trace (§2) — grep across every `.py` file plus `git log`, not inference.
- `tests/domain/test_clinical_bridge.py` + `tests/engine/kme/test_clinical_bridge.py`: **13
  passed, 0 failed** — real coverage of the actually-live threshold gates.
- `parameter_synergies.md` has no entry for B1 (grepped — zero hits), consistent with the registry
  not citing a formal synergy for this pack either.
- §3 thinking-map gate (`cursor-fpf-test-mcp`, `scope="core"`, `risk_level="high"` given the
  pack's own "highest blast radius" framing): three evidence items (Copy A's unwired trace, Copy
  B's live trace with real usage sites, the documentation gap), `attempt_transition()` →
  **`OutcomeKind.CONTINUE`**, zero validation errors, zero missing evidence — CONTINUE held even
  at elevated risk framing.

## 5. Verdict: hold both values, do not touch, flag the disconnect

**No value change proposed or made.** Two independent reasons this stays a "flag, don't touch"
finding rather than a tune-or-fix:

1. The values currently agree (`0.01`/`0.05` both places) — there is no live bug to fix by editing
   a number, only a structural gap (two sources of truth, one dead) to eventually reconcile.
2. Which file should be canonical is an architecture decision, not a documented-parameter toggle —
   squarely inside CHI-006's precedent (spec §5: "may propose, not implement alone... new layer
   logic" applies by extension to "which of two existing hardcoded sources becomes the single one,"
   the same shape of decision as CHI-006's wire-in/retire/align choice for B6).

Three honest options for whoever takes this up (Felix/Gena, per the same routing as CHI-006):

- **Wire Copy A into Copy B**: have `clinical_bridge.py` call
  `get_activation_threshold()`/`get_area_active_threshold()` instead of its own hardcoded
  constants — makes the YAML file's "tune after validation on 20–50 TFP transcripts" instruction
  actually true, and gives `calibrate_thresholds_from_corpus()` a real reason to exist.
  Lowest-risk of the three: `clinical_bridge.py`'s current values become the YAML's committed
  values, so a same-day wire produces zero behavior change — only future edits would then matter.
- **Retire Copy A**: if `clinical_bridge.py`'s hardcoded constants are meant to be the actual
  source of truth going forward, `hesperia/engine/calibration/activation_calibration.py` is dead
  weight (same shape as CHI-006's C6-style deprecation candidate) — delete or clearly mark
  historical, update the catalog/registry to point at `clinical_bridge.py` directly.
- **Leave as-is, document precisely**: lowest-effort — just correct `parameter_catalog.md` §1 and
  the wiki to name `clinical_bridge.py` as the live source and `activation_calibration.py` as an
  unused (not "calibratable") utility. Doesn't fix the structural gap, but stops future sessions
  from believing the YAML file does anything.

No recommendation among the three from Chiron — genuinely an operator/Felix/Gena call on whether
the corpus-calibration workflow the YAML implies is wanted, not something this review can settle.

## 6. Config

No change. Both copies (`activation_calibration.yaml`'s `0.01`/`0.05` and `clinical_bridge.py`'s
`ACTIVATION_THRESHOLD`/`AREA_ACTIVE_THRESHOLD`, also `0.01`/`0.05`) remain exactly as found.

## 7. Invocation (for reference)

Real live behavior today is governed entirely by `clinical_bridge.py`'s hardcoded constants,
exercised whenever `run_session_kme_pipeline()` runs (same TFP-lane orchestrators as every other
pack this session). `activation_calibration.py`'s functions are directly callable in isolation
(as its own tests would, if any existed) but have no effect on any real request.

## 8. Expected output shape (unchanged)

KME node/edge construction (`build_concept_nodes`/`build_family_nodes`/`build_area_nodes`/
area-adjacency edges) — unchanged by this review, since nothing was edited.

## 9. Rollback / registry update

No rollback needed — nothing changed. `CANDIDATE-REGISTRY.md`'s B1 row updated to flag the
disconnect precisely, marking the grind order's final entry as reviewed rather than tuned — this
closes the full Tier B sweep (B1 through B8, minus B6's separate wiring-blocked status) with two
real architecture findings (B1, B6) surfaced honestly rather than eight uniform "held" verdicts.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-21 | B1 (final Tier B pack) reviewed via full thinking-map/pytest toolchain at elevated risk framing — the calibratable YAML is disconnected from the real, heavily-used activation gate in `clinical_bridge.py`; values currently agree, no live drift, no code change; three reconciliation options proposed, routed to triage
