# Agent-facing schemas — ground_truth · GapReport · context_packet

**Date:** 2026-07-19  
**Owner:** Gena (Main developer)  
**Rows:** FPF-PRE07-09 · FPF-MWI-11 (pin note) · FPF-MWI-12 (CLI `climb --full`)  
**Code:** `sphere/router/ground_truth.py` · `sphere/fpf_inspect/schemas.py` · `sphere/fpf_inspect/__main__.py`

---

## MWI-11 pin note

Runtime target pin: **`fpf-thinking-map==1.9.2`** (converged with brain soak).  
GapReport field `fpf_pin` must resolve to that string. Interim dual-pin claims are **forbidden** in agent-facing docs — see [FPF-PIN-HESPERIA-VS-BRAIN.md](FPF-PIN-HESPERIA-VS-BRAIN.md).

---

## 1. ground_truth (`hesperia.agent_response_ground_truth.v0_1`)

Engine-only. Agent **must not** author or edit blocks. Hard-fail if any block empty (`GroundTruthMissingError`).

```json
{
  "schema": "hesperia.agent_response_ground_truth.v0_1",
  "logical": { },
  "weight": { },
  "source_activation": { }
}
```

| Block | Typical keys (engine-derived) |
|-------|-------------------------------|
| `logical` | `engine_trace_present`, `logic_mapping`, `gtp_fired_sides`, `gtp_fired_operators` |
| `weight` | `governance`, `loopability`, `tension_energy`, `obstacle_score`, `risk_level`, `gtp_coherence` |
| `source_activation` | `corpus_snapshot_id`, `policy_snapshot_id`, `retrieval_context_present`, `gtp_current_hex`, `gtp_next_hex` |

**Seams:** `tool_inquiry.py` (MCP/CLI inquire) · `product_interpret_service.py` (HTTP interpret).

---

## 2. GapReport (`hesperia.fpf_gap_report.v0_1`)

Dig face output. Evidence for `hesperia_inspect` re-step — not narrative truth.

```json
{
  "schema": "hesperia.fpf_gap_report.v0_1",
  "lowest_failed_layer": "GTP",
  "gaps": [
    {
      "id": "gap.example",
      "layer_id": "GTP",
      "kind": "provisional_adr|missing_evidence|unfit_exposure|gate_block|coverage",
      "evidence_ids": [],
      "adr_ref": "FPF-HSR-02",
      "advice_hint": "…"
    }
  ],
  "engine_fingerprint": "…",
  "fpf_pin": "fpf-thinking-map==1.9.2"
}
```

**InspectSlice** (per layer): schema `hesperia.fpf_inspect_slice.v0_1` — `engine_authored: true`, three blocks + `fpf` + `provisional` + `fingerprint`.

Climb order: `L0`…`L9` → `GTP` → `Guards` → `Router`. Stub L6 fields never wrap as evidence.

---

## 3. context_packet (allowlist)

Self-contained invoke payload for inquire / dig. **No server session.** Agents pass what the face needs for one call.

**Allow (typical):**

| Key | Use |
|-----|-----|
| `text` / gold fixture string | Synthetic input |
| `analyze_result` / analyze JSON | Dig climb input |
| `thinking_map_outcome` | Last HAND step JSON (kind, missing_evidence, …) |
| `trace_id` | Observability (Noah MWI-22) — no PII |
| `pins` / snapshot ids | Corpus/policy pins when required |

**Deny:**

| Key / content | Why |
|---------------|-----|
| Clinical / TFP patient text | PRE07-12 security |
| Agent-fabricated `logical`/`weight`/`source_activation` | Engine-only |
| `HESPERIA_MCP_BRIDGE_REAL_DATA=1` | Not pre-0.7 agent path |
| Session cookies / UI state | Phase A = no UI |

---

## 4. CLI sugar (MWI-12) — `climb --full`

```bash
cd /data/workspaces/hesperia
python -m sphere.fpf_inspect climb --full --analyze-file path/to/analyze.json
```

- Default climb: `--stop-on-first-gap` (stop early).  
- `--full`: set `stop_on_first_gap=False` — full layer walk + GapReport.  
- `gaps` subcommand: GapReport-only full climb.  
- `probe --layer <id>`: single InspectSlice.  
- `map-step` / `ops-map-step`: HAND steps without MCP.

Same schemas as MCP dig face.

---

`SIGNED: Main developer (Gena) | agent-facing schemas | 2026-07-19 | PRE07-09 MWI-11 pin MWI-12 climb --full`
