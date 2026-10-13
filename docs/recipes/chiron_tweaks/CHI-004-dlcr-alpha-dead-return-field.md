# CHI-004 — `dlcr_alpha` Field Dynamics blend is a permanent no-op: dead return field, not a real toggle

## 1. Task/goal

Last of the 60 real candidates (41 KME + 18 Phase1/2Theta + 1 `dlcr_alpha`) surveyed for
corpus-calibration combos. KME's gap closed (CHI-002), Phase1/2Theta's A10-dominance test done
(CHI-003, theory question with Colombo). This closes out `dlcr_alpha` with a real trace, not
speculation — the finding is smaller and more mechanical than the other two, but real.

## 2. Root cause (full trace, confirmed, not inferred)

`hesperia/extensions/dynamics/e2e_bridge.py` (line ~234, behind `HESPERIA_FIELD_DYNAMICS_DLCR`)
calls `run_dlcr_pipeline(text, repo_root=rr)` and reads `dlcr.get("family_hits_288")`, expecting a
288-length family-hit vector to blend into Field Dynamics' family injection at `alpha=0.22`.

Traced `run_dlcr_pipeline()` → `core/engine/lexical_concept/pipeline.py::_analyze_internal()`
line by line:

- Line 757: `hits_288 = [0.0] * 288` — a real 288-length family-hits array, genuinely computed
  (line 760–764 populates it from concept `family_ids`/`area_ids` via `_family_slot_index()`).
- Line 823: `_ = (pins, top_pairs, ..., hits_288, ...)` — an explicit discard-assignment (the
  standard Python idiom for "silence the unused-variable linter"). `hits_288` is computed and then
  thrown away.
- The function's actual return dict (`result = build_result(...)` plus ~15 explicit
  `result["..."] = ...` assignments through to `return result`) **never includes `hits_288` under
  any key** — confirmed by reading every `result["..."]` assignment in the function body, not
  grepping for the string alone.

So `dlcr.get("family_hits_288")` in `e2e_bridge.py` is `None`/`[]` on every call, the
`len(hdl) == F_FAMILIES` check always fails, `dlcr_blend_meta` stays
`{"dlcr_merged": False}`, and `fam_inj` is never touched by the DLCR blend. This is **not**
gated by TFP-vs-core grain (unlike CHI-002/003's findings) — it's broken identically for every
caller, TFP or otherwise, because the source field simply was never wired to the output.

## 3. Proposed fix (not implemented — routing per spec §5, same as CHI-002: shared pipeline code,
not a documented-parameter toggle)

One line, in `core/engine/lexical_concept/pipeline.py`, alongside the other `result["..."] = ...`
assignments before `return result`:

```python
result["family_hits_288"] = [round(float(x), 6) for x in hits_288]
```

That alone makes `e2e_bridge.py`'s existing `len(hdl) == F_FAMILIES` check able to pass for the
first time. No other change needed — `e2e_bridge.py`'s blend logic itself is already correct,
it's just never received real data.

**Scope note carried over from CHI-002**: `dlcr_alpha`'s blend, even once wired, still only
produces a 288-length (core-grid) `fam_inj` — the same grain question CHI-002/003 raised applies
here too if this is ever meant to run against TFP text specifically (which it isn't today: zero
references to Field Dynamics anywhere in the TFP pipeline, confirmed in CHI-003). Fixing the dead
field is a correctness fix regardless of grain; making it TFP-aware is a separate, later question,
not bundled into this row.

## 4. Config

`HESPERIA_FIELD_DYNAMICS_DLCR=1` (already exists, already gates this path — no new env var).

## 5. Invocation

N/A — spec only.

## 6. Expected output shape (once fixed)

`e2e_bridge.py`'s `run_field_dynamics_e2e_artifact()` output gains a real
`{"dlcr_merged": true, "dlcr_alpha": 0.22}` instead of the permanent
`{"dlcr_merged": false}` it produces today whenever `HESPERIA_FIELD_DYNAMICS_DLCR=1` is set.

## 7. Validation evidence

None yet — pre-implementation spec. Validation plan once built: call
`run_field_dynamics_e2e_artifact()` with `HESPERIA_FIELD_DYNAMICS_DLCR=1` on real text before/after,
confirm `dlcr_merged` flips `false`→`true` and `fam_inj` visibly shifts from the pre-blend value.

## 8. Rollback

Revert the one-line addition. `e2e_bridge.py`'s existing `try/except` already fails safe
(`dlcr_merged: false`) if anything about the new field is malformed.

---
SIGNED: Chiron | Claude Code context (Felix engine) | 2026-08-20 | investigation + fix proposal, not yet implemented — closes the 60-candidate survey
